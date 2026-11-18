import unittest
import uuid
import sys
import os
import json
from io import BytesIO
from PIL import Image
from datetime import datetime, timezone, timedelta

# Ensure local test environment
os.environ["DATABASE_URL"] = "sqlite:///./fixproof_dev.db"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from app.core.database import SessionLocal, Base, engine
from app.models.users import Profile, RoleAssignment
from app.models.localities import Organization, LocalityUnit
from app.models.issues import (
    Issue,
    Submission,
    MediaAsset,
    Asset,
    RecurrenceCandidate,
    TranslationRecord,
    StatusEvent,
)
from app.storage.service import storage_service
from workers.adapters.translation.adapter import translation_adapter, MODEL_ID
from workers.adapters.evidence_assistance.adapter import evidence_assistance_adapter
from app.translations.router import translate_text, TranslationRequest
from app.reports.router import sync_offline_drafts
from app.reports.schemas import OfflineDraftSyncItem
from app.staff.router import (
    get_repair_evidence_assistance,
    link_issue_to_asset,
    LinkAssetRequest,
    get_recurrence_candidates,
    decide_recurrence_candidate,
    RecurrenceDecisionRequest,
)
from app.worker.router import escalate_task, EscalateTaskRequest
from app.public.router import get_public_map_data
from app.core.recurrence import detect_recurrence_candidates

class TestPhase8AdvancedFeatures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.db = SessionLocal()

        cls.org = cls.db.query(Organization).first()
        if not cls.org:
            cls.org = Organization(name="Phase 8 Test Org", code=f"P8-ORG-{uuid.uuid4().hex[:6]}")
            cls.db.add(cls.org)
            cls.db.flush()

        cls.reviewer = cls.db.query(Profile).filter(Profile.email.like("%reviewer%")).first()
        if not cls.reviewer:
            cls.reviewer = Profile(
                auth_user_id="auth-p8-rev",
                full_name="Panchayat Reviewer P8",
                phone_number="+919876543299",
                email="reviewer.p8@panchayat.gov.in",
                is_active=True,
            )
            cls.db.add(cls.reviewer)
            cls.db.flush()

        cls.worker = cls.db.query(Profile).filter(Profile.email.like("%worker%")).first()
        if not cls.worker:
            cls.worker = Profile(
                auth_user_id="auth-p8-worker",
                full_name="Field Worker P8",
                phone_number="+919876543288",
                email="worker.p8@panchayat.gov.in",
                is_active=True,
            )
            cls.db.add(cls.worker)
            cls.db.flush()

        cls.citizen = cls.db.query(Profile).filter(Profile.email.like("%citizen%")).first()
        if not cls.citizen:
            cls.citizen = Profile(
                auth_user_id="auth-p8-citizen",
                full_name="Citizen Tester P8",
                phone_number="+919876543277",
                email="citizen.p8@fixproof.org",
                is_active=True,
            )
            cls.db.add(cls.citizen)
            cls.db.flush()

        cls.db.commit()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_01_translation_never_overwrites_original_text(self):
        """Verifies translations are stored separately, labelled as machine translated, and original text is untouched."""
        original = "Deep pothole near primary school causing accidents"
        req = TranslationRequest(text=original, source_language="en", target_language="kn")
        res = translate_text(req, db=self.db)

        self.assertEqual(res.original_text, original)
        self.assertTrue(res.is_machine_translated)
        self.assertIn("Machine translated", res.disclaimer)
        self.assertIn("ಗುಂಡಿ", res.translated_text)  # Kannada for pothole
        self.assertEqual(res.model_id, MODEL_ID)

        # Check translation record in DB
        record = self.db.query(TranslationRecord).filter(TranslationRecord.original_text == original).first()
        self.assertIsNotNone(record)
        self.assertEqual(record.original_text, original)
        self.assertTrue(record.is_machine_translated)

    def test_02_translation_preserves_tracking_ids_and_coordinates(self):
        """Verifies entity preservation: IDs, coordinates, and phone numbers are not mangled by translation."""
        complex_text = "Water leak near bus stand in issue FP-2026-00412 at 12.5201, 76.8902"
        res_kn = translation_adapter.translate(complex_text, source_lang="en", target_lang="kn")

        self.assertIn("FP-2026-00412", res_kn["translated_text"])
        self.assertIn("12.5201, 76.8902", res_kn["translated_text"])
        self.assertIn("ನೀರು ಸೋರಿಕೆ", res_kn["translated_text"])  # Kannada for water leak

        res_hi = translation_adapter.translate(complex_text, source_lang="en", target_lang="hi")
        self.assertIn("FP-2026-00412", res_hi["translated_text"])
        self.assertIn("12.5201, 76.8902", res_hi["translated_text"])
        self.assertIn("पानी का रिसाव", res_hi["translated_text"])  # Hindi for water leak

    def test_03_before_after_evidence_assistance(self):
        """Verifies before/after image comparison detects changes, flags identical re-uploads, and enforces human review."""
        from PIL import ImageDraw

        img1 = Image.linear_gradient("L").resize((200, 200))
        buf1 = BytesIO()
        img1.save(buf1, format="JPEG")
        bytes1 = buf1.getvalue()

        # 1. Identical photo re-upload check
        res_identical = evidence_assistance_adapter.analyze_evidence_pair(
            before_image=bytes1,
            after_image=bytes1,
            before_hash="same_hash_123",
            after_hash="same_hash_123",
        )
        self.assertTrue(res_identical["insufficient_evidence"])
        self.assertFalse(res_identical["visible_change"])
        self.assertEqual(res_identical["advisory_decision_suggestion"], "REQUEST_EVIDENCE")
        self.assertTrue(res_identical["requires_independent_human_review"])

        # 2. Distinct repaired photo check with patched region
        img2 = img1.copy()
        draw = ImageDraw.Draw(img2)
        draw.rectangle([30, 30, 120, 120], fill=255)
        buf2 = BytesIO()
        img2.save(buf2, format="JPEG")
        bytes2 = buf2.getvalue()

        res_diff = evidence_assistance_adapter.analyze_evidence_pair(
            before_image=bytes1,
            after_image=bytes2,
            before_hash="hash_before",
            after_hash="hash_after",
        )
        self.assertTrue(res_diff["visible_change"])
        self.assertFalse(res_diff["insufficient_evidence"])
        self.assertTrue(res_diff["requires_independent_human_review"])
        self.assertIn("advisory", res_diff["governance_notice"].lower())

    def test_04_idempotent_offline_sync(self):
        """Proves offline sync is strictly idempotent: retrying with same idempotency key never duplicates reports."""
        unique_key = f"OFFLINE-KEY-{uuid.uuid4().hex[:8]}"
        sync_item = OfflineDraftSyncItem(
            client_draft_id="local-uuid-1",
            idempotency_key=unique_key,
            category="road_damage",
            description="Offline drafted pothole report",
            latitude=12.5201,
            longitude=76.8901,
            village_name="Gowdanahalli",
        )

        # 1. First sync call
        res1 = sync_offline_drafts(items=[sync_item], current_user=self.citizen, db=self.db)
        self.assertEqual(res1.synced_count, 1)
        tracking_id_1 = res1.items[0].tracking_id

        # 2. Duplicate retry with same idempotency key
        res2 = sync_offline_drafts(items=[sync_item], current_user=self.citizen, db=self.db)
        self.assertEqual(res2.synced_count, 1)
        tracking_id_2 = res2.items[0].tracking_id

        # Must return the identical existing record without creating duplicate issue
        self.assertEqual(tracking_id_1, tracking_id_2)

        # Check database count
        count = self.db.query(Submission).filter(Submission.description == "Offline drafted pothole report").count()
        self.assertEqual(count, 1)

    def test_05_recurrence_detection_and_adjudication(self):
        """Verifies recurrence candidates flag when a report is near a prior resolved issue, requiring human confirmation."""
        # 1. Create a prior resolved issue
        prior_ref = f"FP-2026-PRIOR-{uuid.uuid4().hex[:6]}"
        prior_issue = Issue(
            reference_number=prior_ref,
            category="water_leak",
            status="RESOLVED",
            priority="MEDIUM",
            latitude=12.5250,
            longitude=76.8950,
            resolved_at=datetime.now(timezone.utc) - timedelta(days=40),
            organization_id=self.org.id,
        )
        self.db.add(prior_issue)
        self.db.flush()

        # 2. Create a new issue 20m away
        new_ref = f"FP-2026-NEW-{uuid.uuid4().hex[:6]}"
        new_issue = Issue(
            reference_number=new_ref,
            category="water_leak",
            status="SUBMITTED",
            priority="MEDIUM",
            latitude=12.5251,
            longitude=76.8951,
            organization_id=self.org.id,
        )
        self.db.add(new_issue)
        self.db.commit()

        # 3. Run recurrence detection
        candidates = detect_recurrence_candidates(
            db=self.db,
            new_issue_id=new_issue.id,
            category="water_leak",
            latitude=12.5251,
            longitude=76.8951,
        )
        self.assertGreaterEqual(len(candidates), 1)
        cand = next((c for c in candidates if c.prior_issue_id == prior_issue.id), None)
        self.assertIsNotNone(cand, f"Prior issue {prior_issue.id} not found in candidates: {[c.prior_issue_id for c in candidates]}")
        self.assertEqual(cand.decision, "PENDING")

        # 4. Human reviewer confirms recurrence and boosts priority
        dec_req = RecurrenceDecisionRequest(
            decision="CONFIRMED_RECURRENCE",
            notes="Water leak recurring at same joint clamp",
            priority_boost="HIGH",
        )
        dec_res = decide_recurrence_candidate(candidate_id=cand.id, req=dec_req, current_reviewer=self.reviewer, db=self.db)

        self.assertEqual(dec_res["decision"], "CONFIRMED_RECURRENCE")
        self.assertTrue(dec_res["is_recurrence"])
        self.assertEqual(dec_res["new_priority"], "HIGH")

        # Verify database update
        self.db.refresh(new_issue)
        self.assertTrue(new_issue.is_recurrence)
        self.assertEqual(new_issue.prior_resolved_issue_id, prior_issue.id)
        self.assertEqual(new_issue.priority, "HIGH")

    def test_06_asset_register_and_linking(self):
        """Verifies verified municipal asset querying and linking to physical issues."""
        asset = self.db.query(Asset).first()
        self.assertIsNotNone(asset, "Pilot assets must be present in database.")

        issue_ref = f"FP-2026-ASSET-{uuid.uuid4().hex[:6]}"
        issue = Issue(
            reference_number=issue_ref,
            category="road_damage",
            status="SUBMITTED",
            organization_id=self.org.id,
        )
        self.db.add(issue)
        self.db.commit()

        # Link issue to verified physical asset
        link_req = LinkAssetRequest(asset_id=asset.id)
        res = link_issue_to_asset(id=issue.id, req=link_req, current_reviewer=self.reviewer, db=self.db)

        self.assertEqual(res["status"], "linked")
        self.assertEqual(res["asset_id"], asset.id)

        self.db.refresh(issue)
        self.assertEqual(issue.asset_id, asset.id)

    def test_07_worker_operational_escalation(self):
        """Verifies worker can flag blocked tasks requiring operational escalation and supervisor notification."""
        issue_ref = f"FP-2026-ESC-{uuid.uuid4().hex[:6]}"
        issue = Issue(
            reference_number=issue_ref,
            category="road_damage",
            status="ASSIGNED",
            organization_id=self.org.id,
        )
        self.db.add(issue)
        self.db.commit()

        esc_req = EscalateTaskRequest(
            reason="NEEDS_MATERIALS",
            explanation="Requires 2 tons of asphalt premix not available in GP store.",
        )
        res = escalate_task(issue_id=issue.id, req=esc_req, current_worker=self.worker, db=self.db)

        self.assertEqual(res["status"], "escalated")
        self.assertTrue(res["is_escalated"])

        self.db.refresh(issue)
        self.assertTrue(issue.is_escalated)
        self.assertIn("NEEDS_MATERIALS", issue.escalation_reason)

    def test_08_public_map_data_privacy_sanitization(self):
        """Verifies public map endpoint returns generalized coordinates and excludes private citizen details."""
        points = get_public_map_data(db=self.db)
        self.assertGreater(len(points), 0)

        for pt in points:
            # Lat/lon must be generalized to 3 decimal places (~100m)
            lat_str = str(pt.public_latitude)
            decimals = len(lat_str.split(".")[1]) if "." in lat_str else 0
            self.assertLessEqual(decimals, 3, "Privacy violation: Public map coordinates must be generalized!")
            self.assertIsNotNone(pt.reference_number)
            self.assertIsNotNone(pt.category)
            self.assertIsNotNone(pt.status)

if __name__ == "__main__":
    unittest.main()
