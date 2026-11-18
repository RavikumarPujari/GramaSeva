import unittest
import uuid
import sys
import os
import json
from io import BytesIO
from PIL import Image
from datetime import datetime, timezone

# Ensure test environment
os.environ["DATABASE_URL"] = "sqlite:///./fixproof_dev.db"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from app.core.database import SessionLocal, Base, engine
from app.models.users import Profile, RoleAssignment
from app.models.localities import Organization, LocalityUnit
from app.models.issues import Issue, Submission, MediaAsset, DuplicateCandidate
from app.storage.service import storage_service
from workers.adapters.water_leak.adapter import (
    water_leak_adapter,
    EXPECTED_LEAK_SHA256,
    WaterLeakAdapter,
)
from workers.adapters.duplicate.similarity import (
    compute_haversine_distance,
    compute_spatial_score,
    compute_text_similarity,
    compute_dhash,
    compute_visual_similarity,
    rank_duplicate_candidate,
)
from app.staff.router import get_duplicate_candidates, decide_duplicate
from app.staff.schemas import DuplicateDecisionRequest
from app.reports.router import get_report_duplicate_suggestions
from app.ai.router import get_categories_ai_capabilities, get_ai_models_health

class TestDuplicatesAndAICandidates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.db = SessionLocal()

        cls.org = cls.db.query(Organization).first()
        if not cls.org:
            cls.org = Organization(name="Dup Test Org", code=f"DUP-ORG-{uuid.uuid4().hex[:6]}")
            cls.db.add(cls.org)
            cls.db.flush()

        cls.reviewer = cls.db.query(Profile).filter(Profile.email.like("%reviewer%")).first()
        if not cls.reviewer:
            cls.reviewer = Profile(
                auth_user_id="auth-reviewer-test",
                full_name="Panchayat Reviewer Test",
                phone_number="+919876543210",
                email="reviewer.test@panchayat.gov.in",
                is_active=True,
            )
            cls.db.add(cls.reviewer)
            cls.db.flush()

        cls.citizen = cls.db.query(Profile).filter(Profile.email.like("%citizen%")).first()
        if not cls.citizen:
            cls.citizen = Profile(
                auth_user_id="auth-citizen-test",
                full_name="Citizen Tester",
                phone_number="+919876500001",
                email="citizen.test@fixproof.org",
                is_active=True,
            )
            cls.db.add(cls.citizen)
            cls.db.flush()

        cls.db.commit()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_01_multi_signal_duplicate_ranking_math(self):
        """Verifies spatial, text, and visual similarity computations combine into transparent score and explanation."""
        # 1. Spatial distance test
        dist = compute_haversine_distance(12.5200, 76.8900, 12.5202, 76.8902)
        self.assertGreater(dist, 0.0)
        self.assertLess(dist, 100.0)  # ~30 meters

        spatial_score = compute_spatial_score(dist, max_radius=300.0)
        self.assertGreater(spatial_score, 0.8)

        # 2. Text similarity
        text1 = "Severe pothole on main road near bus shelter"
        text2 = "Large pothole on main road outside bus stand"
        text_score = compute_text_similarity(text1, text2)
        self.assertGreater(text_score, 0.4)

        # 3. Visual dHash
        img1 = Image.new("RGB", (200, 200), color="blue")
        img2 = Image.new("RGB", (200, 200), color="blue")
        h1 = compute_dhash(img1)
        h2 = compute_dhash(img2)
        self.assertEqual(len(h1), 16)
        vis_score = compute_visual_similarity(h1, h2)
        self.assertEqual(vis_score, 1.0)

        # 4. Multi-signal ranking
        res = rank_duplicate_candidate(
            sub_lat=12.5200,
            sub_lon=76.8900,
            sub_desc=text1,
            sub_hash=h1,
            issue_lat=12.5202,
            issue_lon=76.8902,
            issue_desc=text2,
            issue_hash=h2,
            category_match=True,
        )
        self.assertGreaterEqual(res["composite_score"], 0.70)
        self.assertTrue(res["is_strong_candidate"])
        self.assertIn("Matching category", res["explanation"])
        self.assertIn("visual image similarity", res["explanation"])

    def test_02_no_automatic_duplicate_merge(self):
        """Verifies that duplicate candidate queries NEVER auto-merge; human reviewer must decide."""
        # Create base issue
        ref_base = f"FP-2026-DUP-{uuid.uuid4().hex[:6]}"
        issue = Issue(
            reference_number=ref_base,
            category="water_leak",
            status="UNDER_REVIEW",
            priority="HIGH",
            latitude=12.5210,
            longitude=76.8910,
            organization_id=self.org.id,
        )
        self.db.add(issue)
        self.db.flush()

        sub1 = Submission(
            issue_id=issue.id,
            reporter_id=self.citizen.id,
            tracking_id=f"FP-2026-SUB1-{uuid.uuid4().hex[:4]}",
            category="water_leak",
            description="Leaking water pipe at junction",
            latitude=12.5210,
            longitude=76.8910,
        )
        self.db.add(sub1)

        # Create separate submission nearby
        sub2 = Submission(
            issue_id=None,  # Not linked yet
            reporter_id=self.citizen.id,
            tracking_id=f"FP-2026-SUB2-{uuid.uuid4().hex[:4]}",
            category="water_leak",
            description="Continuous water leakage near road edge",
            latitude=12.5211,
            longitude=76.8911,
        )
        self.db.add(sub2)
        self.db.commit()

        # Query candidates for sub2
        candidates = get_duplicate_candidates(
            submission_id=sub2.id,
            current_reviewer=self.reviewer,
            db=self.db,
        )

        # Must find the candidate
        self.assertGreaterEqual(len(candidates), 1)
        found = next((c for c in candidates if c.issue_id == issue.id), None)
        self.assertIsNotNone(found)
        self.assertIsNotNone(found.composite_score)
        self.assertIsNotNone(found.explanation)

        # STRICT ASSERTION: sub2 must NOT be auto-merged into issue
        self.db.refresh(sub2)
        self.assertIsNone(sub2.issue_id, "VIOLATION: Sub2 was auto-merged without human decision!")

        # Now execute explicit human decision: KEEP_SEPARATE
        dec_req = DuplicateDecisionRequest(
            submission_id=sub2.id,
            target_issue_id=issue.id,
            decision="KEEP_SEPARATE",
            reason="Two separate water pipe leaks on opposite sides of road",
        )
        dec_res = decide_duplicate(req=dec_req, current_reviewer=self.reviewer, db=self.db)
        self.assertEqual(dec_res["decision"], "REJECTED_DIFFERENT")

        # Verify audit record in duplicate_candidates table
        audit = (
            self.db.query(DuplicateCandidate)
            .filter(DuplicateCandidate.submission_id == sub2.id, DuplicateCandidate.target_issue_id == issue.id)
            .first()
        )
        self.assertIsNotNone(audit)
        self.assertEqual(audit.decision, "REJECTED_DIFFERENT")
        self.assertEqual(audit.adjudicated_by_id, self.reviewer.id)

    def test_03_exact_copy_image_detection(self):
        """Proves exact byte match (identical image upload) achieves visual similarity 1.0."""
        # Generate random image bytes
        buf = BytesIO()
        Image.new("RGB", (100, 100), color=(200, 50, 50)).save(buf, format="JPEG")
        raw_bytes = buf.getvalue()

        # Compute SHA-256
        import hashlib
        h1 = hashlib.sha256(raw_bytes).hexdigest()
        h2 = hashlib.sha256(raw_bytes).hexdigest()

        # Exact match rule
        score = compute_visual_similarity(h1, h2, is_exact_sha_match=True)
        self.assertEqual(score, 1.0)

    def test_04_water_leak_model_forward_pass(self):
        """Validates real MSunusi pipeline leak YOLO model checkpoint verification and forward pass."""
        readiness = water_leak_adapter.check_readiness()
        self.assertTrue(readiness["ready"], f"Model load failed: {readiness.get('error')}")
        self.assertEqual(readiness["model_id"], "msunusi-pipeline-leak-yolo")
        self.assertEqual(readiness["checkpoint_sha256"], EXPECTED_LEAK_SHA256)
        self.assertIn("water", readiness["classes"])
        self.assertIn("leak", readiness["classes"])

        # Run real forward pass on an image fixture
        test_img = Image.new("RGB", (640, 640), color=(50, 120, 200))
        pred = water_leak_adapter.predict(test_img)

        self.assertIn(pred["status"], ["completed", "no_detections"])
        self.assertEqual(pred["task"], "water_leak_detection")
        self.assertEqual(pred["model_id"], "msunusi-pipeline-leak-yolo")
        self.assertEqual(pred["model_revision"], EXPECTED_LEAK_SHA256)
        self.assertTrue(pred["requires_human_review"])
        self.assertGreater(pred["latency_ms"], 0)
        self.assertIn("water", pred["prompt_message"].lower())

    def test_05_unsupported_category_fallback(self):
        """Confirms solid waste and unverified categories gracefully fall back to manual review with auditable record."""
        capabilities = get_categories_ai_capabilities()
        self.assertGreaterEqual(len(capabilities), 4)

        # Road damage & water leak have active models
        rdd = next((c for c in capabilities if c.category == "road_damage"), None)
        self.assertIsNotNone(rdd)
        self.assertEqual(rdd.status, "ACTIVE_MODEL")
        self.assertTrue(rdd.requires_human_confirmation)

        leak = next((c for c in capabilities if c.category == "water_leak"), None)
        self.assertIsNotNone(leak)
        self.assertEqual(leak.status, "ACTIVE_MODEL")

        # Solid waste (TACO) falls back to manual review
        garbage = next((c for c in capabilities if c.category == "garbage_dump"), None)
        self.assertIsNotNone(garbage)
        self.assertEqual(garbage.status, "MANUAL_FALLBACK")
        self.assertIsNone(garbage.model_id)
        self.assertIn("TACO", garbage.evaluation_notes)
        self.assertIn("incompatible", garbage.evaluation_notes.lower())

    def test_06_model_health_registry(self):
        """Confirms GET /ai/models/health returns live health for both Road Damage and Water Leak models."""
        health_list = get_ai_models_health()
        self.assertEqual(len(health_list), 2)
        model_ids = [h.model_id for h in health_list]
        self.assertIn("oracl4-rdd-yolov8s", model_ids)
        self.assertIn("msunusi-pipeline-leak-yolo", model_ids)

        for h in health_list:
            self.assertTrue(h.ready)
            self.assertIsNotNone(h.checkpoint_sha256)
            self.assertGreater(len(h.classes), 0)

    def test_07_citizen_duplicate_suggestions(self):
        """Validates that citizen reporting duplicate suggestions API returns ranked advisory results without auto-merging."""
        # Create an existing issue
        ref_issue = f"FP-2026-SUG-{uuid.uuid4().hex[:6]}"
        target_issue = Issue(
            reference_number=ref_issue,
            category="road_damage",
            status="ASSIGNED",
            priority="HIGH",
            latitude=12.5300,
            longitude=76.8950,
            organization_id=self.org.id,
        )
        self.db.add(target_issue)
        self.db.flush()

        target_sub = Submission(
            issue_id=target_issue.id,
            reporter_id=self.citizen.id,
            tracking_id=f"FP-2026-TGT-{uuid.uuid4().hex[:4]}",
            category="road_damage",
            description="Deep crater on main road near bus stop",
            latitude=12.5300,
            longitude=76.8950,
        )
        self.db.add(target_sub)

        # Citizen drafts a report 20m away
        new_sub = Submission(
            issue_id=None,
            reporter_id=self.citizen.id,
            tracking_id=f"FP-2026-NEW-{uuid.uuid4().hex[:4]}",
            category="road_damage",
            description="Pothole near bus stop",
            latitude=12.5301,
            longitude=76.8951,
        )
        self.db.add(new_sub)
        self.db.commit()

        # Query duplicate suggestions for citizen
        suggestions = get_report_duplicate_suggestions(id=new_sub.id, db=self.db)
        self.assertGreaterEqual(len(suggestions), 1)

        matching_sug = next((s for s in suggestions if s.issue_id == target_issue.id), None)
        self.assertIsNotNone(matching_sug, f"Target issue {target_issue.id} not found in suggestions: {[s.issue_id for s in suggestions]}")
        self.assertGreater(matching_sug.composite_score, 0.40)
        self.assertIn("Matching category", matching_sug.explanation)
        self.assertLess(matching_sug.distance_meters, 50.0)

        # Confirm new_sub remains unlinked
        self.db.refresh(new_sub)
        self.assertIsNone(new_sub.issue_id)

if __name__ == "__main__":
    unittest.main()
