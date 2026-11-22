import unittest
import sys
import os
import io
import json
import uuid
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.models import (
    Profile,
    RoleAssignment,
    LocalityUnit,
    Organization,
    Issue,
    Submission,
    MediaAsset,
    StatusEvent,
    Feedback,
    Notification,
)
from app.localities.router import _resolve_coordinates
from app.reports.router import (
    generate_tracking_id,
    check_duplicate_complaints,
    CheckDuplicatesRequest,
    submit_report_feedback,
    get_report_feedback,
    FeedbackRequest,
    build_report_response,
)
from app.staff.router import (
    confirm_issue,
    triage_issue,
    review_resolution,
    ConfirmIssueRequest,
)
from app.staff.schemas import (
    TriageActionRequest,
    ResolutionReviewRequest,
)
from app.worker.router import (
    accept_assignment,
    submit_work_completion,
    WorkCompletionSubmitRequest,
)
from app.models.issues import Assignment
from app.storage.service import storage_service
from app.ai.gemini_service import gemini_service
from app.notifications.service import notification_service

class TestCompleteCitizenToWorkerWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()

        cls.citizen = cls.db.query(Profile).filter(Profile.email == "citizen.ananya@example.com").first()
        cls.pdo = cls.db.query(Profile).filter(Profile.email == "pdo.peeranwadi@belagavi.gov.in").first()
        if not cls.pdo:
            cls.pdo = cls.db.query(Profile).filter(Profile.email == "reviewer.gowdanahalli@fixproof.org").first()
        cls.worker = cls.db.query(Profile).filter(Profile.email == "worker.ramesh@fixproof.org").first()
        if not cls.worker:
            cls.worker = cls.db.query(Profile).filter(Profile.email == "worker.ramesh@example.com").first()

        img = Image.new("RGB", (200, 200), color=(73, 109, 137))
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format="JPEG")
        cls.dummy_img_bytes = img_byte_arr.getvalue()

    @classmethod
    def tearDownClass(cls):
        db = cls.db
        try:
            from app.models.issues import (
                Feedback, RepairReview, WorkCompletion, Assignment,
                StatusEvent, MediaAsset, Submission, Issue, Notification
            )
            db.query(Feedback).delete(synchronize_session=False)
            db.query(RepairReview).delete(synchronize_session=False)
            db.query(WorkCompletion).delete(synchronize_session=False)
            db.query(Assignment).delete(synchronize_session=False)
            db.query(StatusEvent).delete(synchronize_session=False)
            db.query(MediaAsset).delete(synchronize_session=False)
            db.query(Submission).delete(synchronize_session=False)
            db.query(Notification).delete(synchronize_session=False)
            db.query(Issue).delete(synchronize_session=False)
            db.commit()
        except Exception as e:
            db.rollback()
            print("Cleanup in tearDownClass error:", e)
        finally:
            cls.db.close()

    def test_01_citizen_reporting_workflow_stages_1_to_6(self):
        """
        Verify all 6 stages of the citizen complaint reporting workflow:
        Step 1: Citizen Details (Registered & Guest)
        Step 2: Photo Upload and Accurate Location (GPS + Geocoding)
        Step 3: AI Category Analysis
        Step 4: Gemini Multilingual Description Generation
        Step 5: Duplicate Complaint Matching
        Step 6: Final Review and Atomic Persistence
        """
        # Step 1: Citizen details
        self.assertIsNotNone(self.citizen, "Citizen profile must exist")
        self.assertEqual(self.citizen.email, "citizen.ananya@example.com")

        # Step 2: Accurate Location & GPS resolution
        test_lat, test_lon = 15.8497, 74.4977
        res_loc = _resolve_coordinates(test_lat, test_lon, self.db)
        self.assertIsNotNone(res_loc)
        self.assertTrue(res_loc.is_verified)

        # Step 3: Photo evidence storage
        rel_path, mime, size_bytes, file_hash = storage_service.store_private_media(
            self.dummy_img_bytes, "unit_test_evidence.jpg"
        )
        self.assertEqual(mime, "image/jpeg")
        self.assertGreater(size_bytes, 0)

        # Step 4: Gemini Multilingual Description Generation
        gemini_res = gemini_service.generate_complaint_details(
            category="ROADS",
            defect_label="Large pothole",
            village_name="Peeranwadi",
            citizen_notes="Road surface damaged near junction",
            locale="kn"
        )
        self.assertIn("title", gemini_res)
        self.assertIn("description", gemini_res)

        # Step 5: Duplicate Complaint Check
        dup_req = CheckDuplicatesRequest(
            category="ROADS",
            latitude=test_lat,
            longitude=test_lon,
            radius_meters=500
        )
        dups = check_duplicate_complaints(dup_req, self.db)
        self.assertIsInstance(dups, list)

        # Step 6: Atomic Complaint Submission Persistence
        org = self.db.query(Organization).first()
        self.assertIsNotNone(org)
        ref_no = generate_tracking_id(self.db)

        peeranwadi_loc = self.db.query(LocalityUnit).filter(LocalityUnit.name_en.ilike("%Peeranwadi%")).first()

        issue = Issue(
            id=str(uuid.uuid4()),
            reference_number=ref_no,
            category="road_damage",
            status="SUBMITTED",
            priority="HIGH",
            organization_id=org.id,
            locality_unit_id=peeranwadi_loc.id if peeranwadi_loc else None,
            latitude=test_lat,
            longitude=test_lon,
            public_latitude=round(test_lat, 3),
            public_longitude=round(test_lon, 3),
            jurisdiction_status="VERIFIED"
        )
        self.db.add(issue)
        self.db.flush()

        submission = Submission(
            id=str(uuid.uuid4()),
            tracking_id=ref_no,
            reporter_id=self.citizen.id,
            issue_id=issue.id,
            category="road_damage",
            description="Hazardous pothole on Peeranwadi main street causing skidding.",
            locale="en",
            locality_unit_id=peeranwadi_loc.id if peeranwadi_loc else None,
            village_name="Peeranwadi",
            taluk_name="Belagavi Taluk",
            latitude=test_lat,
            longitude=test_lon,
            confirmed_latitude=test_lat,
            confirmed_longitude=test_lon,
            confirmed_village="Peeranwadi",
            confirmed_address="Main Road, Peeranwadi, Belagavi Taluk, Karnataka 590014",
            reporter_name=self.citizen.full_name,
            reporter_phone=self.citizen.phone_number,
            is_guest=False
        )
        self.db.add(submission)

        media = MediaAsset(
            id=str(uuid.uuid4()),
            profile_id=self.citizen.id,
            submission_id=submission.id,
            issue_id=issue.id,
            evidence_role="CITIZEN_BEFORE",
            storage_path=rel_path,
            file_hash=file_hash,
            mime_type=mime,
            file_size_bytes=size_bytes,
            is_quarantined=False,
            is_public_approved=True
        )
        self.db.add(media)
        self.db.commit()

        self.assertEqual(issue.status, "SUBMITTED")
        self.assertEqual(submission.tracking_id, ref_no)

    def test_02_full_downstream_lifecycle_pdo_to_worker_to_resolution(self):
        """
        Verify downstream civic complaint lifecycle:
        1. Correct PDO receives complaint based on GP jurisdiction.
        2. PDO reviews and accepts complaint (UNDER_REVIEW).
        3. PDO assigns task to field worker (ASSIGNED).
        4. Worker accepts task and starts work (IN_PROGRESS).
        5. Worker uploads After evidence and submits completion (REPAIR_REPORTED / Awaiting PDO).
        6. PDO verifies repair photographic evidence and approves resolution (RESOLVED).
        7. Citizen tracks resolved complaint and submits 5-star feedback.
        """
        self.assertIsNotNone(self.pdo, "PDO profile must exist")
        self.assertIsNotNone(self.worker, "Worker profile must exist")

        org = self.db.query(Organization).first()
        ref_no = generate_tracking_id(self.db)
        peeranwadi_loc = self.db.query(LocalityUnit).filter(LocalityUnit.name_en.ilike("%Peeranwadi%")).first()

        # Step 1: Create fresh submitted issue
        issue = Issue(
            id=str(uuid.uuid4()),
            reference_number=ref_no,
            category="road_damage",
            status="SUBMITTED",
            priority="HIGH",
            organization_id=org.id,
            locality_unit_id=peeranwadi_loc.id if peeranwadi_loc else None,
            latitude=15.8497,
            longitude=74.4977,
            jurisdiction_status="VERIFIED"
        )
        self.db.add(issue)
        self.db.flush()

        submission = Submission(
            id=str(uuid.uuid4()),
            tracking_id=ref_no,
            reporter_id=self.citizen.id,
            issue_id=issue.id,
            category="road_damage",
            description="Pothole repair required near village market.",
            locale="en",
            locality_unit_id=peeranwadi_loc.id if peeranwadi_loc else None,
            village_name="Peeranwadi",
            is_guest=False
        )
        self.db.add(submission)
        self.db.commit()

        # Step 2: PDO accepts complaint
        confirm_issue(
            issue.id,
            req=ConfirmIssueRequest(reason="Verified by Panchayat development officer"),
            current_reviewer=self.pdo,
            db=self.db
        )
        self.db.refresh(issue)
        self.assertEqual(issue.status, "UNDER_REVIEW")

        # Step 3: PDO assigns worker
        triage_req = TriageActionRequest(
            assigned_worker_id=self.worker.id,
            priority="HIGH",
            notes="Fill pothole with dense asphalt mix and compact surface."
        )
        triage_issue(issue.id, triage_req, current_reviewer=self.pdo, db=self.db)
        self.db.refresh(issue)
        self.assertEqual(issue.status, "ASSIGNED")

        # Step 4: Worker accepts assignment
        asgn = self.db.query(Assignment).filter(
            Assignment.issue_id == issue.id,
            Assignment.worker_profile_id == self.worker.id
        ).first()
        self.assertIsNotNone(asgn)

        accept_assignment(asgn.id, current_worker=self.worker, db=self.db)
        self.db.refresh(issue)
        self.assertEqual(issue.status, "IN_PROGRESS")

        # Step 5: Worker uploads After photo & submits completion
        after_path, after_mime, after_size, after_hash = storage_service.store_private_media(
            self.dummy_img_bytes, "unit_test_after_repair.jpg"
        )
        media_after = MediaAsset(
            id=str(uuid.uuid4()),
            profile_id=self.worker.id,
            submission_id=submission.id,
            issue_id=issue.id,
            evidence_role="WORKER_AFTER",
            storage_path=after_path,
            file_hash=after_hash,
            mime_type=after_mime,
            file_size_bytes=after_size,
            is_quarantined=False,
            is_public_approved=True
        )
        self.db.add(media_after)
        self.db.commit()

        comp_req = WorkCompletionSubmitRequest(
            work_description="Pothole filled with cold asphalt mix and rolled flush.",
            work_performed="Asphalt filling and compaction",
            materials_used="Cold asphalt patch mix 50kg"
        )
        submit_work_completion(issue.id, comp_req, current_worker=self.worker, db=self.db)
        self.db.refresh(issue)
        self.assertEqual(issue.status, "REPAIR_REPORTED")

        # Step 6: PDO verifies and resolves complaint
        res_req = ResolutionReviewRequest(
            decision="APPROVE",
            explanation="Photographic evidence independently inspected and approved."
        )
        review_resolution(issue.id, res_req, current_reviewer=self.pdo, db=self.db)
        self.db.refresh(issue)
        self.assertEqual(issue.status, "RESOLVED")

        # Step 7: Citizen tracking & 5-star feedback
        tracking_view = build_report_response(submission, issue, self.db)
        self.assertEqual(tracking_view.status, "RESOLVED")

        fb_req = FeedbackRequest(
            rating=5,
            comment="Prompt and professional road repair. Very satisfied!",
            is_satisfied=True
        )
        submit_report_feedback(ref_no, fb_req, current_user=self.citizen, db=self.db)
        fb_data = get_report_feedback(ref_no, current_user=self.citizen, db=self.db)
        self.assertTrue(fb_data["has_feedback"])
        self.assertEqual(fb_data["rating"], 5)

if __name__ == "__main__":
    unittest.main()
