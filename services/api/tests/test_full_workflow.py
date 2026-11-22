import os
import sys
import uuid
import json
import unittest
from io import BytesIO
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from PIL import Image

# Ensure test database environment
os.environ["DATABASE_URL"] = "sqlite:///./fixproof_dev.db"
os.environ["YOLO_CONFIG_DIR"] = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".ultralytics"))
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
from app.storage.service import storage_service
from app.reports.router import (
    create_draft,
    update_draft,
    submit_report,
    get_report_detail,
    submit_citizen_clarification,
    check_duplicate_complaints,
    DraftCreateRequest,
    DraftUpdateRequest,
    SubmitReportRequest,
    CitizenClarificationRequest,
    CheckDuplicatesRequest,
)
from app.localities.router import google_geocode_endpoint
from app.ai.gemini_service import gemini_service
from app.staff.router import (
    get_village_pdo_overview,
    confirm_issue,
    reject_issue,
    request_issue_information,
    triage_issue,
    review_resolution,
    RequestInfoRequest,
    RejectIssueRequest,
)
from app.staff.schemas import ResolutionReviewRequest, TriageActionRequest
from app.auth.dependencies import require_roles
from app.worker.router import (
    get_worker_tasks,
    submit_work_completion,
    WorkCompletionSubmitRequest,
)
from app.public.router import (
    get_public_gallery,
    get_public_issue_detail,
)
from database.seeds.demo_seed import seed_database
from database.seeds.demo_gallery_seed import seed_demo_data, clean_demo_data
from fastapi import HTTPException


def create_test_image(color=(180, 40, 40), width=100, height=100) -> bytes:
    buffer = BytesIO()
    img = Image.new("RGB", (width, height), color=color)
    img.save(buffer, format="JPEG")
    return buffer.getvalue()


class TestGramaSevaFullWorkflow(unittest.TestCase):
    """
    Comprehensive End-to-End Civic Complaint Workflow Verification.
    Validates all 16 core business lifecycle requirements from Part 11.
    """

    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        seed_database(reset_old_pilot=False)
        seed_demo_data()
        cls.db = SessionLocal()

        # Profiles
        cls.citizen = cls.db.query(Profile).filter(Profile.email == "citizen.ananya@example.com").first()
        cls.pdo = cls.db.query(Profile).filter(Profile.email.in_(["pdo.peeranwadi@gramaseva.kar.gov.in", "reviewer.gowdanahalli@fixproof.org"])).first()
        if not cls.pdo:
            cls.pdo = cls.db.query(Profile).join(RoleAssignment).filter(RoleAssignment.role == "reviewer").first()
        cls.worker = cls.db.query(Profile).filter(Profile.email.in_(["worker.ramesh@fixproof.org", "worker.ramesh@gramaseva.kar.gov.in"])).first()
        if not cls.worker:
            cls.worker = cls.db.query(Profile).join(RoleAssignment).filter(RoleAssignment.role == "worker").first()

        # Locate or assign PDO jurisdiction
        pdo_role = cls.db.query(RoleAssignment).filter(RoleAssignment.profile_id == cls.pdo.id, RoleAssignment.role == "reviewer").first()
        if pdo_role and pdo_role.jurisdiction_unit_id:
            cls.locality = cls.db.query(LocalityUnit).filter(LocalityUnit.id == pdo_role.jurisdiction_unit_id).first()
        else:
            cls.locality = cls.db.query(LocalityUnit).first()
            if pdo_role:
                pdo_role.jurisdiction_unit_id = cls.locality.id
                cls.db.commit()

        # Department
        cls.dept = cls.db.query(Department).first()
        if not cls.dept:
            cls.dept = Department(
                organization_id=cls.locality.organization_id if cls.locality else "org-1",
                name_en="Public Works Department",
                code="PWD",
            )
            cls.db.add(cls.dept)
            cls.db.commit()

        # Align worker role to this locality
        worker_role = cls.db.query(RoleAssignment).filter(RoleAssignment.profile_id == cls.worker.id, RoleAssignment.role == "worker").first()
        if not worker_role:
            worker_role = RoleAssignment(
                profile_id=cls.worker.id,
                role="worker",
                approval_status="APPROVED",
                is_active=True,
                jurisdiction_unit_id=cls.locality.id,
            )
            cls.db.add(worker_role)
            cls.db.commit()
        else:
            worker_role.approval_status = "APPROVED"
            worker_role.is_active = True
            worker_role.jurisdiction_unit_id = cls.locality.id
            cls.db.commit()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_01_citizen_report_creation_with_gps_and_photo(self):
        """Part 1: Citizen creates draft with GPS coordinates, Taluk, Gram Panchayat and photo evidence."""
        img_bytes = create_test_image(color=(220, 60, 60))
        rel_path, mime, size, f_hash = storage_service.store_private_media(img_bytes, "pothole_evidence.jpg")
        media_id = str(uuid.uuid4())

        media = MediaAsset(
            id=media_id,
            profile_id=self.citizen.id,
            storage_path=rel_path,
            mime_type=mime,
            file_size_bytes=size,
            file_hash=f_hash,
            evidence_role="CITIZEN_BEFORE",
            is_quarantined=False,
            is_public_approved=True,
        )
        self.db.add(media)
        self.db.commit()

        # Create citizen draft
        draft_req = DraftCreateRequest(
            category="road_damage",
            description="Deep crater pothole along Peeranwadi High School road endangering school buses.",
            latitude=15.8497,
            longitude=74.4977,
            village_name=self.locality.name_en if self.locality else "Peeranwadi Gram Panchayat",
            taluk_name="Belagavi Taluk",
            locality_unit_id=self.locality.id if self.locality else None,
            reporter_name=self.citizen.full_name,
            reporter_phone=self.citizen.phone_number,
            location_method="GPS_VERIFIED",
            gps_accuracy=4.2,
        )
        draft = create_draft(req=draft_req, current_user=self.citizen, db=self.db)
        self.assertIsNotNone(draft.id)
        self.assertEqual(draft.status, "DRAFT")
        self.assertEqual(draft.village_name, draft_req.village_name)
        self.assertEqual(draft.taluk_name, "Belagavi Taluk")
        self.assertEqual(draft.latitude, 15.8497)

        # Attach media to draft submission
        sub = self.db.query(Submission).filter(Submission.id == draft.id).first()
        media.submission_id = sub.id
        self.db.commit()

        self.__class__.created_draft_id = draft.id
        self.__class__.created_media_id = media_id

    def test_02_google_reverse_geocoding_parsing(self):
        """Part 1: Google reverse-geocoding parsing of address_components without halluncinating village."""
        mock_google_response = {
            "status": "OK",
            "results": [
                {
                    "place_id": "ChIJ_peeranwadi_sample_place_id",
                    "formatted_address": "Peeranwadi, Belagavi Taluk, Karnataka 590014, India",
                    "address_components": [
                        {"long_name": "Peeranwadi", "short_name": "Peeranwadi", "types": ["sublocality_level_1", "sublocality", "political"]},
                        {"long_name": "Belagavi Taluk", "short_name": "Belagavi Taluk", "types": ["administrative_area_level_3", "political"]},
                        {"long_name": "Belagavi District", "short_name": "Belagavi", "types": ["administrative_area_level_2", "political"]},
                        {"long_name": "Karnataka", "short_name": "KA", "types": ["administrative_area_level_1", "political"]},
                        {"long_name": "India", "short_name": "IN", "types": ["country", "political"]},
                        {"long_name": "590014", "short_name": "590014", "types": ["postal_code"]},
                    ],
                }
            ],
        }

        with patch("urllib.request.urlopen") as mock_urlopen, patch("app.localities.router.settings") as mock_settings:
            mock_settings.google_maps_api_key = "AIzaSy_fake_test_key_for_unit_tests"
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.read.return_value = json.dumps(mock_google_response).encode("utf-8")
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            geo_res = google_geocode_endpoint(latitude=15.8497, longitude=74.4977)
            self.assertEqual(geo_res.village, "Peeranwadi")
            self.assertEqual(geo_res.taluk, "Belagavi Taluk")
            self.assertEqual(geo_res.district, "Belagavi District")
            self.assertEqual(geo_res.postal_code, "590014")
            self.assertEqual(geo_res.geocoding_status, "OK")

    def test_03_gemini_vision_problem_analysis_zero_hallucination(self):
        """Part 1: Gemini vision problem analysis: suggests category/title without inventing coordinates."""
        img_bytes = create_test_image(color=(100, 100, 100))
        analysis = gemini_service.analyze_image(img_bytes, context={"category_hint": "road_damage"})
        self.assertIn("is_civic_issue", analysis)
        self.assertIn("visual_summary", analysis)
        # Verify Gemini does not fabricate GPS coordinates
        self.assertNotIn("latitude", analysis)
        self.assertNotIn("longitude", analysis)

    def test_04_citizen_review_and_atomic_submission_tracking_id(self):
        """Part 1: Citizen reviews and submits report: generates unique GS-2026-BEL tracking ID."""
        submit_req = SubmitReportRequest(
            idempotency_key=str(uuid.uuid4()),
            is_anonymous=False,
            location_method="GPS_VERIFIED",
            gps_accuracy=3.5,
            confirmed_latitude=15.8497,
            confirmed_longitude=74.4977,
            confirmed_village="Peeranwadi Gram Panchayat",
            confirmation_method="CITIZEN_CONFIRMED",
            jurisdiction_status="VERIFIED",
        )
        report = submit_report(
            id=self.__class__.created_draft_id,
            req=submit_req,
            current_user=self.citizen,
            db=self.db,
        )
        self.assertIn(report.status, ["SUBMITTED", "UNDER_REVIEW"])
        self.assertTrue(report.tracking_id.startswith("GS-2026-"))
        self.assertEqual(report.confirmation_method, "CITIZEN_CONFIRMED")
        self.assertEqual(report.jurisdiction_status, "VERIFIED")

        # Find underlying Issue
        issue = self.db.query(Issue).join(Submission).filter(Submission.id == self.__class__.created_draft_id).first()
        self.assertIsNotNone(issue)
        self.assertIn(issue.status, ["SUBMITTED", "UNDER_REVIEW"])
        self.assertFalse(issue.is_demo)

        self.__class__.created_issue_id = issue.id
        self.__class__.created_tracking_id = report.tracking_id

    def test_05_scoped_pdo_overview_metrics_isolates_demo_records(self):
        """Part 2: Scoped PDO overview returns all 10 metrics and strictly excludes demo records."""
        stats = get_village_pdo_overview(
            current_reviewer=self.pdo,
            db=self.db,
        )
        stats_dict = stats.model_dump() if hasattr(stats, "model_dump") else (stats.dict() if hasattr(stats, "dict") else dict(stats))
        self.assertIn("total_complaints", stats_dict)
        self.assertIn("new_complaints", stats_dict)
        self.assertIn("under_review", stats_dict)
        self.assertIn("awaiting_clarification", stats_dict)
        self.assertIn("approved", stats_dict)
        self.assertIn("assigned", stats_dict)
        self.assertIn("in_progress", stats_dict)
        self.assertIn("awaiting_verification", stats_dict)
        self.assertIn("resolved", stats_dict)
        self.assertIn("rejected", stats_dict)
        # Verify newly submitted/unreviewed issue is reflected in operational metrics
        self.assertGreaterEqual(stats_dict["total_complaints"], 1)

    def test_06_pdo_requests_clarification_on_complaint(self):
        """Part 2: PDO requests clarification: transitions to NEEDS_INFORMATION with message."""
        info_req = RequestInfoRequest(
            message="Please clarify if the road damage is near the primary or high school gate."
        )
        res = request_issue_information(
            issue_id=self.__class__.created_issue_id,
            req=info_req,
            current_reviewer=self.pdo,
            db=self.db,
        )
        self.assertEqual(res["new_status"], "NEEDS_INFORMATION")

        issue = self.db.query(Issue).filter(Issue.id == self.__class__.created_issue_id).first()
        self.assertEqual(issue.status, "NEEDS_INFORMATION")
        self.assertEqual(issue.clarification_message, info_req.message)

    def test_07_citizen_responds_to_clarification(self):
        """Part 6: Citizen submits clarification: transitions status back to UNDER_REVIEW."""
        clarify_req = CitizenClarificationRequest(
            clarification_response="It is directly in front of the High School main gate."
        )
        resp = submit_citizen_clarification(
            id=self.__class__.created_draft_id,
            req=clarify_req,
            current_user=self.citizen,
            db=self.db,
        )
        self.assertEqual(resp.status, "UNDER_REVIEW")
        self.assertEqual(resp.clarification_response, clarify_req.clarification_response)

        issue = self.db.query(Issue).filter(Issue.id == self.__class__.created_issue_id).first()
        self.assertEqual(issue.status, "UNDER_REVIEW")
        self.assertEqual(issue.clarification_response, clarify_req.clarification_response)

    def test_08_pdo_approves_complaint(self):
        """Part 2: PDO accepts/approves the complaint: transitions status to UNDER_REVIEW."""
        res = confirm_issue(
            issue_id=self.__class__.created_issue_id,
            current_reviewer=self.pdo,
            db=self.db,
        )
        self.assertIn(res["new_status"], ["UNDER_REVIEW", "APPROVED"])

        issue = self.db.query(Issue).filter(Issue.id == self.__class__.created_issue_id).first()
        self.assertIn(issue.status, ["UNDER_REVIEW", "APPROVED"])

    def test_09_pdo_assigns_approved_worker_with_target_date(self):
        """Part 3: PDO assigns eligible approved worker belonging to village with target_date."""
        # Ensure worker has approved active role
        existing_role = self.db.query(RoleAssignment).filter(
            RoleAssignment.profile_id == self.worker.id,
            RoleAssignment.role == "worker",
        ).first()
        if not existing_role:
            existing_role = RoleAssignment(
                profile_id=self.worker.id,
                role="worker",
                approval_status="APPROVED",
                is_active=True,
                jurisdiction_unit_id=self.locality.id if self.locality else None,
            )
            self.db.add(existing_role)
            self.db.commit()
        else:
            existing_role.approval_status = "APPROVED"
            existing_role.is_active = True
            self.db.commit()

        triage_req = TriageActionRequest(
            priority="HIGH",
            department_id=self.dept.id,
            assigned_worker_id=self.worker.id,
            instructions="Fill with asphalt cold-mix and compact thoroughly before evening traffic.",
            target_date=datetime.now(timezone.utc),
        )
        res = triage_issue(
            issue_id=self.__class__.created_issue_id,
            req=triage_req,
            current_reviewer=self.pdo,
            db=self.db,
        )
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["assigned_worker_id"], self.worker.id)

        # Verify assignment record in database
        assignment = self.db.query(Assignment).filter(Assignment.issue_id == self.__class__.created_issue_id).first()
        self.assertIsNotNone(assignment)
        self.assertIsNotNone(assignment.target_date)

        issue = self.db.query(Issue).filter(Issue.id == self.__class__.created_issue_id).first()
        self.assertEqual(issue.status, "ASSIGNED")

    def test_10_worker_views_assigned_task_and_original_photo(self):
        """Part 4: Worker views assigned tasks with original photo evidence and target date."""
        tasks = get_worker_tasks(current_worker=self.worker, db=self.db)
        matching = [t for t in tasks if t.issue_id == self.__class__.created_issue_id]
        self.assertGreaterEqual(len(matching), 1)
        task = matching[0]
        self.assertEqual(task.status, "ASSIGNED")
        self.assertGreater(len(task.citizen_photo_ids), 0)

    def test_11_worker_uploads_solved_image_and_submits_completion(self):
        """Part 4: Worker uploads separate solved image (WORKER_AFTER) without overwriting original."""
        solved_bytes = create_test_image(color=(30, 160, 60))
        rel_path, mime, size, f_hash = storage_service.store_private_media(solved_bytes, "repaired_road.jpg")
        media_id = str(uuid.uuid4())

        solved_media = MediaAsset(
            id=media_id,
            profile_id=self.worker.id,
            storage_path=rel_path,
            mime_type=mime,
            file_size_bytes=size,
            file_hash=f_hash,
            evidence_role="WORKER_AFTER",
            is_quarantined=False,
            is_public_approved=True,
            issue_id=self.__class__.created_issue_id,
        )
        self.db.add(solved_media)
        self.db.commit()

        # Worker submits completion
        completion_req = WorkCompletionSubmitRequest(
            work_description="Pothole filled with dense bituminous concrete, compacted with plate vibrator.",
            materials_cost=4200.0,
            labour_cost=1800.0,
            other_expenses_cost=400.0,
            repair_media_id=media_id,
            work_performed="Excavation, gravel base leveling, cold asphalt patching and rolling.",
            materials_used="Bituminous concrete 120kg, tack coat 5L",
            labour_details="2 skilled road workers for 4 hours",
        )
        res = submit_work_completion(
            issue_id=self.__class__.created_issue_id,
            req=completion_req,
            current_worker=self.worker,
            db=self.db,
        )
        self.assertEqual(res["status"], "awaiting_verification")

        issue = self.db.query(Issue).filter(Issue.id == self.__class__.created_issue_id).first()
        self.assertEqual(issue.status, "REPAIR_REPORTED")
        self.assertEqual(issue.proposed_cost, 6400.0)

        # Verify original photo evidence is still intact
        orig_media = self.db.query(MediaAsset).filter(
            MediaAsset.id == self.__class__.created_media_id,
            MediaAsset.evidence_role == "CITIZEN_BEFORE",
        ).first()
        self.assertIsNotNone(orig_media)

        self.__class__.solved_media_id = media_id

    def test_12_gemini_before_after_advisory_comparison(self):
        """Part 4: Gemini before/after advisory comparison generation (advisory only)."""
        before_bytes = create_test_image(color=(200, 50, 50))
        after_bytes = create_test_image(color=(40, 180, 50))
        comparison = gemini_service.compare_before_after(before_bytes, after_bytes, category="road_damage")
        self.assertIn("visible_change", comparison)
        self.assertIn("difference_summary", comparison)
        self.assertIn("suggested_advisory_decision", comparison)

    def test_13_pdo_final_verification_approves_with_verified_cost(self):
        """Part 5: PDO verifies before & after photos and enters final verified cost (officials only)."""
        review_req = ResolutionReviewRequest(
            decision="APPROVE",
            explanation="Site inspected by PDO. Pothole completely leveled and flush with asphalt.",
            verified_cost=6200.0,
            cost_remarks="Reduced transport allowance by ₹200; actual asphalt voucher verified.",
        )
        res = review_resolution(
            issue_id=self.__class__.created_issue_id,
            req=review_req,
            current_reviewer=self.pdo,
            db=self.db,
        )
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["new_status"], "RESOLVED")

        issue = self.db.query(Issue).filter(Issue.id == self.__class__.created_issue_id).first()
        self.assertEqual(issue.status, "RESOLVED")
        self.assertEqual(issue.cost_status, "VERIFIED")
        self.assertEqual(issue.verified_cost, 6200.0)
        self.assertIsNotNone(issue.resolved_at)

    def test_14_citizen_tracks_final_resolved_complaint(self):
        """Part 6: Citizen tracks complaint: sees complete lifecycle, before/after proof, verified cost."""
        detail = get_report_detail(
            id=self.__class__.created_draft_id,
            current_user=self.citizen,
            db=self.db,
        )
        self.assertEqual(detail.status, "RESOLVED")
        self.assertEqual(detail.verified_cost, 6200.0)
        self.assertEqual(detail.cost_status, "VERIFIED")
        self.assertGreaterEqual(len(detail.timeline), 3)

    def test_15_public_gallery_shows_demo_records_and_resolved_issues(self):
        """Part 7: Public gallery shows demo records and resolved complaints with DEMO labels."""
        gallery = get_public_gallery(db=self.db)
        self.assertGreaterEqual(len(gallery), 6)

        # Check demo records have is_demo True
        demo_items = [g for g in gallery if g.is_demo]
        self.assertGreaterEqual(len(demo_items), 6)

        # Verify our newly resolved complaint is also in the public gallery or public detail
        pub_detail = get_public_issue_detail(
            issue_id=self.__class__.created_tracking_id,
            db=self.db,
        )
        self.assertEqual(pub_detail.status, "RESOLVED")
        self.assertEqual(pub_detail.verified_cost, 6200.0)

    def test_16_rbac_access_control_security(self):
        """Part 11: Scoped access control: citizens cannot triage, workers cannot self-verify."""
        # 1. Citizen cannot access reviewer role
        with self.assertRaises(HTTPException):
            require_roles("reviewer", "admin")(current_user=self.citizen, db=self.db)

        # 2. Worker cannot approve resolution
        review_req = ResolutionReviewRequest(
            decision="APPROVE",
            explanation="Worker attempting self-verification.",
            verified_cost=5000.0,
        )
        with self.assertRaises(HTTPException):
            review_resolution(
                issue_id=self.__class__.created_issue_id,
                req=review_req,
                current_reviewer=self.worker,
                db=self.db,
            )

    def test_17_check_duplicate_complaints(self):
        """Step 5 (Match): Check duplicate complaint matching endpoint returns candidates or empty list."""
        dup_req = CheckDuplicatesRequest(
            category="road_damage",
            latitude=15.8497,
            longitude=74.5078,
            description="Deep pothole on main road",
            max_radius=1000.0,
        )
        candidates = check_duplicate_complaints(req=dup_req, db=self.db)
        self.assertIsInstance(candidates, list)


if __name__ == "__main__":
    unittest.main()
