import unittest
import uuid
import sys
import os
from datetime import datetime, timezone

# Ensure local test environment
os.environ["DATABASE_URL"] = "sqlite:///./fixproof_dev.db"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from app.core.database import SessionLocal, Base, engine
from app.models.users import Profile, RoleAssignment
from app.models.localities import LocalityUnit, Organization, Department
from app.models.issues import (
    Issue,
    Submission,
    StatusEvent,
    MediaAsset,
    Assignment,
    WorkCompletion,
    AIBeforeAfterAnalysis,
)
from app.worker.router import (
    submit_work_completion,
    get_worker_tasks,
    WorkCompletionSubmitRequest,
)
from app.staff.router import (
    review_resolution,
    get_all_complaints,
)
from app.staff.schemas import ResolutionReviewRequest
from app.public.router import get_public_issues, get_public_issue_detail
from app.auth.security import hash_password
from database.seeds.demo_seed import seed_database
from fastapi import HTTPException


class TestWorkCompletionAndCosts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        seed_database(reset_old_pilot=False)
        cls.db = SessionLocal()

        # Organization & Department
        cls.org = cls.db.query(Organization).first()
        if not cls.org:
            cls.org = Organization(name="Belagavi Taluk Administration", code="BTA")
            cls.db.add(cls.org)
            cls.db.commit()
            cls.db.refresh(cls.org)

        cls.dept = cls.db.query(Department).first()
        if not cls.dept:
            cls.dept = Department(
                name_en="Public Works Department",
                name_kn="ಲೋಕೋಪಯೋಗಿ ಇಲಾಖೆ",
                name_hi="लोक निर्माण विभाग",
                code="PWD",
                organization_id=cls.org.id,
            )
            cls.db.add(cls.dept)
            cls.db.commit()
            cls.db.refresh(cls.dept)

        # Admin
        cls.admin = cls.db.query(Profile).filter(Profile.email == "admin@fixproof.org").first()

        # Village Locality
        cls.village = (
            cls.db.query(LocalityUnit)
            .filter(LocalityUnit.name_en == "Peeranwadi")
            .first()
        )
        if not cls.village:
            cls.village = LocalityUnit(
                name_en="Peeranwadi",
                name_kn="ಪೀರಣವಾಡಿ",
                unit_type="GP",
                official_code="KA-BEL-PRW",
                is_active=True,
                taluk_name="Belagavi Taluk",
                district_name="Belagavi",
                state_name="Karnataka",
                latitude=15.8322,
                longitude=74.4533,
            )
            cls.db.add(cls.village)
            cls.db.commit()
            cls.db.refresh(cls.village)

        # PDO / Reviewer for Peeranwadi
        cls.pdo = cls.db.query(Profile).filter(Profile.email == "pdo.peeranwadi@belagavi.gov.in").first()
        if not cls.pdo:
            cls.pdo = Profile(
                email="pdo.peeranwadi@belagavi.gov.in",
                password_hash=hash_password("DemoPassword123!"),
                full_name="Basavaraj Patil",
                preferred_locale="kn",
            )
            cls.db.add(cls.pdo)
            cls.db.flush()
            cls.db.add(
                RoleAssignment(
                    profile_id=cls.pdo.id,
                    role="reviewer",
                    jurisdiction_unit_id=cls.village.id,
                    is_active=True,
                )
            )
            cls.db.commit()

        # Field Worker
        cls.worker = cls.db.query(Profile).filter(Profile.email == "worker.ramesh@fixproof.org").first()
        if not cls.worker:
            cls.worker = Profile(
                email="worker.ramesh@fixproof.org",
                password_hash=hash_password("DemoPassword123!"),
                full_name="Ramesh K.",
                preferred_locale="kn",
            )
            cls.db.add(cls.worker)
            cls.db.flush()
            cls.db.add(
                RoleAssignment(
                    profile_id=cls.worker.id,
                    role="worker",
                    jurisdiction_unit_id=cls.village.id,
                    is_active=True,
                    approval_status="APPROVED",
                )
            )
            cls.db.commit()

        # Citizen (consent = False for privacy testing)
        cls.citizen = cls.db.query(Profile).filter(Profile.email == "citizen.ananya@example.com").first()
        if not cls.citizen:
            cls.citizen = Profile(
                email="citizen.ananya@example.com",
                password_hash=hash_password("DemoPassword123!"),
                full_name="Ananya Sharma",
                phone_number="+91 98765 43210",
                preferred_locale="en",
            )
            cls.db.add(cls.citizen)
            cls.db.flush()
            cls.db.add(
                RoleAssignment(
                    profile_id=cls.citizen.id,
                    role="citizen",
                    is_active=True,
                )
            )
            cls.db.commit()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def tearDown(self):
        self.db.rollback()

    def setUp(self):
        # Create an isolated test issue for each test run
        ref_num = f"GS-TEST-{uuid.uuid4().hex[:6].upper()}"
        self.issue = Issue(
            reference_number=ref_num,
            category="road_damage",
            status="IN_PROGRESS",
            priority="HIGH",
            organization_id=self.org.id,
            locality_unit_id=self.village.id,
            assigned_worker_id=self.worker.id,
            latitude=15.8325,
            longitude=74.4538,
            estimated_cost=2500.0,
            public_display_consent=False,
        )
        self.db.add(self.issue)
        self.db.flush()

        # Submission
        self.submission = Submission(
            issue_id=self.issue.id,
            reporter_id=self.citizen.id,
            tracking_id=f"TRK-{uuid.uuid4().hex[:8].upper()}",
            category="road_damage",
            description="Deep pothole near Peeranwadi primary school gate.",
            village_name="Peeranwadi",
            ward_name="Ward 1",
            public_display_consent=False,
        )
        self.db.add(self.submission)
        self.db.flush()

        # Assignment
        self.assignment = Assignment(
            issue_id=self.issue.id,
            department_id=self.dept.id,
            worker_profile_id=self.worker.id,
            status="ACCEPTED",
            instructions="Fill pothole with 40mm aggregate base and bitumen seal.",
        )
        self.db.add(self.assignment)
        self.db.flush()

        # Citizen Before Media
        self.before_media = MediaAsset(
            issue_id=self.issue.id,
            submission_id=self.submission.id,
            profile_id=self.citizen.id,
            evidence_role="CITIZEN_BEFORE",
            storage_path="test/citizen_before.jpg",
            file_hash="hash_before_12345",
            mime_type="image/jpeg",
            file_size_bytes=102400,
            is_quarantined=False,
            is_public_approved=False,
        )
        self.db.add(self.before_media)

        # Worker After Media
        self.after_media = MediaAsset(
            issue_id=self.issue.id,
            profile_id=self.worker.id,
            evidence_role="WORKER_AFTER",
            storage_path="test/worker_after.jpg",
            file_hash="hash_after_67890",
            mime_type="image/jpeg",
            file_size_bytes=104800,
            is_quarantined=False,
            is_public_approved=False,
        )
        self.db.add(self.after_media)
        self.db.commit()

    def test_01_worker_completion_submission_and_costs(self):
        """Worker submits completion with photos, materials, labour, and itemized proposed costs."""
        req = WorkCompletionSubmitRequest(
            work_description="Repaired road pothole using cold mix asphalt and manual roller compaction.",
            work_performed="Excavated loose rubble, laid 40mm aggregate, compacted with bitumen top seal.",
            materials_used="2 bags bitumen cold mix (₹800), 0.5 brass aggregate (₹400)",
            labour_details="1 skilled mason (₹1,000), 1 assistant (₹500)",
            materials_cost=1200.0,
            labour_cost=1500.0,
            other_expenses_cost=300.0,
            proposed_cost=3000.0,
            completion_date="2026-11-21",
            after_media_ids=[self.after_media.id],
        )

        resp = submit_work_completion(
            issue_id=self.issue.id,
            req=req,
            current_worker=self.worker,
            db=self.db,
        )

        self.assertEqual(resp["status"], "awaiting_verification")
        self.assertEqual(resp["cost_status"], "PROPOSED")
        self.assertEqual(resp["proposed_cost"], 3000.0)

        # Refresh issue from DB
        self.db.refresh(self.issue)
        # STRICT GOVERNANCE: Status must be REPAIR_REPORTED ("Awaiting Verification"), NOT RESOLVED
        self.assertEqual(self.issue.status, "REPAIR_REPORTED")
        self.assertEqual(self.issue.materials_cost, 1200.0)
        self.assertEqual(self.issue.labour_cost, 1500.0)
        self.assertEqual(self.issue.other_expenses_cost, 300.0)
        self.assertEqual(self.issue.proposed_cost, 3000.0)
        self.assertEqual(self.issue.cost_status, "PROPOSED")
        self.assertIsNone(self.issue.verified_cost)  # Unverified!

        # WorkCompletion record created
        comp = (
            self.db.query(WorkCompletion)
            .filter(WorkCompletion.issue_id == self.issue.id)
            .first()
        )
        self.assertIsNotNone(comp)
        self.assertEqual(comp.status, "AWAITING_VERIFICATION")
        self.assertEqual(comp.proposed_cost, 3000.0)
        self.assertEqual(comp.worker_profile_id, self.worker.id)

        # AI Before/After advisory analysis executed
        ai_record = (
            self.db.query(AIBeforeAfterAnalysis)
            .filter(AIBeforeAfterAnalysis.issue_id == self.issue.id)
            .first()
        )
        self.assertIsNotNone(ai_record)
        self.assertIn("visual_consistency_score", resp["ai_analysis"])
        self.assertIn("advisory_decision_suggestion", resp["ai_analysis"])

    def test_02_separation_of_duty_enforced(self):
        """Worker cannot approve their own repair or verified expenditure."""
        # Submit completion first
        req = WorkCompletionSubmitRequest(
            work_description="Work completed.",
            materials_cost=1000.0,
            labour_cost=1000.0,
            proposed_cost=2000.0,
            after_media_ids=[self.after_media.id],
        )
        submit_work_completion(self.issue.id, req, self.worker, self.db)

        # Worker attempts to call review_resolution
        review_req = ResolutionReviewRequest(
            decision="APPROVE",
            explanation="Self-approving my own repair work.",
            verified_cost=2000.0,
        )

        with self.assertRaises(HTTPException) as ctx:
            review_resolution(self.issue.id, review_req, self.worker, self.db)

        self.assertIn(ctx.exception.status_code, [403, 401])

    def test_03_pdo_rework_rejection_and_worker_resubmission(self):
        """PDO rejects inadequate completion; issue transitions to CORRECTION_REQUIRED with PDO remarks."""
        # 1. Worker submits
        req = WorkCompletionSubmitRequest(
            work_description="Quick patch done.",
            materials_cost=500.0,
            labour_cost=500.0,
            proposed_cost=1000.0,
            after_media_ids=[self.after_media.id],
        )
        submit_work_completion(self.issue.id, req, self.worker, self.db)

        # 2. PDO inspects and returns for correction
        reject_req = ResolutionReviewRequest(
            decision="CORRECTION_REQUIRED",
            explanation="Surface aggregate is loose. Re-compact with mechanical tamper and seal edges.",
            cost_remarks="Proposed labour cost rejected pending proper compaction.",
        )
        review_resolution(self.issue.id, reject_req, self.pdo, self.db)

        self.db.refresh(self.issue)
        self.assertEqual(self.issue.status, "CORRECTION_REQUIRED")
        self.assertEqual(self.issue.cost_status, "REJECTED")
        self.assertIn("Re-compact", self.issue.resolution_review_notes)

        # 3. Worker queries tasks: receives PDO remarks
        tasks = get_worker_tasks(self.worker, self.db)
        my_task = next((t for t in tasks if t.issue_id == self.issue.id), None)
        self.assertIsNotNone(my_task)
        self.assertEqual(my_task.status, "CORRECTION_REQUIRED")
        self.assertIn("compaction", (my_task.pdo_remarks or "").lower())

        # 4. Worker resubmits revised completion
        revised_req = WorkCompletionSubmitRequest(
            work_description="Re-compacted with mechanical tamper and applied new hot emulsion edge seal.",
            materials_cost=700.0,
            labour_cost=800.0,
            proposed_cost=1500.0,
            after_media_ids=[self.after_media.id],
        )
        submit_work_completion(self.issue.id, revised_req, self.worker, self.db)

        self.db.refresh(self.issue)
        self.assertEqual(self.issue.status, "REPAIR_REPORTED")
        self.assertEqual(self.issue.proposed_cost, 1500.0)

    def test_04_pdo_approval_and_verified_expenditure(self):
        """PDO approves resolution with verified cost; marks issue RESOLVED and approves public media."""
        # 1. Worker submits
        req = WorkCompletionSubmitRequest(
            work_description="Complete resurfacing per specifications.",
            work_performed="Excavation and asphalt overlay",
            materials_used="Cold mix 3 bags",
            labour_details="2 workers 1 day",
            materials_cost=1500.0,
            labour_cost=1800.0,
            other_expenses_cost=200.0,
            proposed_cost=3500.0,
            after_media_ids=[self.after_media.id],
        )
        submit_work_completion(self.issue.id, req, self.worker, self.db)

        # 2. PDO reviews and approves with final audited cost
        approve_req = ResolutionReviewRequest(
            decision="APPROVE",
            explanation="Inspected in person at Peeranwadi school gate. High quality road compaction verified.",
            verified_cost=3500.0,
            cost_remarks="Approved per standard Gram Panchayat PWD schedule of rates.",
        )
        review_resolution(self.issue.id, approve_req, self.pdo, self.db)

        self.db.refresh(self.issue)
        self.assertEqual(self.issue.status, "RESOLVED")
        self.assertEqual(self.issue.cost_status, "VERIFIED")
        self.assertEqual(self.issue.verified_cost, 3500.0)
        self.assertIsNotNone(self.issue.resolved_at)

        # Safe media is now approved for public transparency
        after_asset = self.db.query(MediaAsset).filter(MediaAsset.id == self.after_media.id).first()
        self.assertTrue(after_asset.is_public_approved)

    def test_05_public_transparency_privacy_and_expenditure_display(self):
        """Verifies public endpoint privacy masking, village filters, and expenditure display rules."""
        # 1. Complete resolution for the test issue
        req = WorkCompletionSubmitRequest(
            work_description="Drainage clearing completed.",
            materials_cost=400.0,
            labour_cost=600.0,
            proposed_cost=1000.0,
            after_media_ids=[self.after_media.id],
        )
        submit_work_completion(self.issue.id, req, self.worker, self.db)

        approve_req = ResolutionReviewRequest(
            decision="APPROVE",
            explanation="Drain unblocked and water flowing cleanly.",
            verified_cost=1000.0,
            cost_remarks="Verified expenditure bill attached.",
        )
        review_resolution(self.issue.id, approve_req, self.pdo, self.db)

        # 2. Query public issues list with Belagavi village filter
        public_list = get_public_issues(
            village_name="Peeranwadi",
            status_filter="RESOLVED",
            db=self.db,
        )

        match = next((item for item in public_list if item.id == self.issue.id), None)
        self.assertIsNotNone(match)
        # Privacy: citizen consent is False -> citizen_name MUST be masked as "Verified Citizen"
        self.assertEqual(match.reporter_display_name, "Verified Citizen")
        # Verified expenditure is visible
        self.assertEqual(match.verified_cost, 1000.0)
        self.assertEqual(match.cost_status, "VERIFIED")
        # Village name matches
        self.assertEqual(match.village_name, "Peeranwadi")

        # 3. Query public detail
        detail = get_public_issue_detail(self.issue.id, self.db)
        self.assertEqual(detail.reporter_display_name, "Verified Citizen")
        self.assertEqual(detail.verified_cost, 1000.0)
        self.assertIsNotNone(detail.work_completion_description)


if __name__ == "__main__":
    unittest.main()
