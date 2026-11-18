import unittest
import sys
import os
import uuid
from io import BytesIO
from PIL import Image
from fastapi import HTTPException

# Add services/api and root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from app.core.database import SessionLocal, Base, engine
from app.models import Profile, Submission, Issue, MediaAsset, Assignment, StatusEvent, LocalityUnit, Department, Organization
from app.storage.service import storage_service
from app.reports.router import (
    create_draft,
    submit_report,
    dispute_report,
    DraftCreateRequest,
    SubmitReportRequest,
    DisputeRequest,
)
from app.staff.router import (
    get_reviewer_inbox,
    triage_issue,
    get_duplicate_candidates,
    decide_duplicate,
    get_resolution_queue,
    review_resolution,
    TriageActionRequest,
    DuplicateDecisionRequest,
    ResolutionReviewRequest,
)
from app.worker.router import (
    get_worker_tasks,
    accept_assignment,
    request_resolution_review,
    RequestReviewRequest,
)
from database.seeds.demo_seed import seed_database

def generate_test_jpeg(width=120, height=120, color=(200, 50, 50)) -> bytes:
    buffer = BytesIO()
    img = Image.new("RGB", (width, height), color=color)
    img.save(buffer, format="JPEG")
    return buffer.getvalue()

class TestManualIssueLifecycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed_database()
        cls.db = SessionLocal()
        cls.citizen_a = cls.db.query(Profile).filter(Profile.email == "citizen.ananya@example.com").first()
        cls.citizen_b = cls.db.query(Profile).filter(Profile.email == "citizen.suresh@example.com").first()
        cls.rev_gowd = cls.db.query(Profile).filter(Profile.email == "reviewer.gowdanahalli@fixproof.org").first()
        cls.rev_town = cls.db.query(Profile).filter(Profile.email == "reviewer.town@fixproof.org").first()
        cls.worker = cls.db.query(Profile).filter(Profile.email == "worker.ramesh@fixproof.org").first()
        cls.admin = cls.db.query(Profile).filter(Profile.email == "admin@fixproof.org").first()
        cls.dept_roads = cls.db.query(Department).filter(Department.code == "DEPT-ROADS").first()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_01_full_report_to_resolution_journey(self):
        """
        Verify end-to-end report-to-resolution journey:
        Citizen Report -> Reviewer Triage -> Worker Accept -> Worker Repair Proof -> Independent Reviewer Approval.
        """
        # 1. Citizen submits report with photo evidence
        ward_gowd = self.db.query(LocalityUnit).filter(LocalityUnit.official_code == "W2-GOWD").first()
        draft = create_draft(
            DraftCreateRequest(
                category="road_damage",
                description="Large pothole near primary school gate",
                village_name="Gowdanahalli",
                ward_name=ward_gowd.name_en,
                locality_unit_id=ward_gowd.id,
                latitude=12.5120,
                longitude=76.6210,
            ),
            self.citizen_a,
            self.db,
        )

        # Upload photo
        rel_path, mime, size, f_hash = storage_service.store_private_media(
            generate_test_jpeg(100, 100, (180, 40, 40)), "pothole_before.jpg"
        )
        before_media = MediaAsset(
            profile_id=self.citizen_a.id,
            submission_id=draft.id,
            issue_id=self.db.query(Submission).filter(Submission.id == draft.id).first().issue_id,
            evidence_role="CITIZEN_BEFORE",
            storage_path=rel_path,
            mime_type=mime,
            file_size_bytes=size,
            file_hash=f_hash,
            is_quarantined=True,
        )
        self.db.add(before_media)
        self.db.commit()

        submitted = submit_report(draft.id, SubmitReportRequest(), self.citizen_a, self.db)
        self.assertEqual(submitted.status, "SUBMITTED")

        # 2. Authority Reviewer sees it in jurisdiction inbox
        inbox = get_reviewer_inbox(status_filter="SUBMITTED", current_reviewer=self.rev_gowd, db=self.db)
        matched = next((item for item in inbox if item.submission_id == draft.id), None)
        self.assertIsNotNone(matched)
        issue_id = matched.issue_id

        # 3. Reviewer triages, confirms priority HIGH, routes to Roads Dept, and assigns Ramesh
        triage_res = triage_issue(
            issue_id,
            TriageActionRequest(
                priority="HIGH",
                department_id=self.dept_roads.id,
                assigned_worker_id=self.worker.id,
                instructions="Fill with gravel compaction and apply asphalt seal",
                audit_reason="Verified pothole obstructing school bus transit",
            ),
            self.rev_gowd,
            self.db,
        )
        self.assertEqual(triage_res["new_status"], "ASSIGNED")

        # 4. Worker opens assigned tasks
        worker_tasks = get_worker_tasks(current_worker=self.worker, db=self.db)
        assigned_task = next((t for t in worker_tasks if t.issue_id == issue_id), None)
        self.assertIsNotNone(assigned_task)

        # 5. Worker accepts task
        accept_res = accept_assignment(assigned_task.assignment_id, current_worker=self.worker, db=self.db)
        self.assertEqual(accept_res["status"], "in_progress")

        issue_obj = self.db.query(Issue).filter(Issue.id == issue_id).first()
        self.assertEqual(issue_obj.status, "IN_PROGRESS")

        # 6. Worker uploads repair proof (WORKER_AFTER)
        rel_path_after, mime_a, size_a, f_hash_a = storage_service.store_private_media(
            generate_test_jpeg(100, 100, (40, 180, 40)), "repaired_road.jpg"
        )
        after_media = MediaAsset(
            profile_id=self.worker.id,
            issue_id=issue_id,
            evidence_role="WORKER_AFTER",
            storage_path=rel_path_after,
            mime_type=mime_a,
            file_size_bytes=size_a,
            file_hash=f_hash_a,
            is_quarantined=False,
        )
        self.db.add(after_media)
        self.db.commit()

        # 7. Worker requests resolution review
        req_rev = request_resolution_review(
            issue_id,
            RequestReviewRequest(work_summary="Completed asphalt patching and roller compaction"),
            current_worker=self.worker,
            db=self.db,
        )
        self.assertEqual(req_rev["new_status"], "REPAIR_REPORTED")

        # 8. Independent Reviewer reviews resolution queue
        queue = get_resolution_queue(current_reviewer=self.rev_gowd, db=self.db)
        queued_issue = next((q for q in queue if q.issue_id == issue_id), None)
        self.assertIsNotNone(queued_issue)
        self.assertGreaterEqual(len(queued_issue.after_photo_ids), 1)

        # 9. Reviewer approves resolution independently
        approved = review_resolution(
            issue_id,
            ResolutionReviewRequest(
                decision="APPROVE",
                explanation="Inspected after-photos; patch compaction meets local road quality standard",
            ),
            self.rev_gowd,
            self.db,
        )
        self.assertEqual(approved["new_status"], "RESOLVED")
        self.assertIsNotNone(approved["resolved_at"])

        # 10. Verify audit timeline completeness
        events = self.db.query(StatusEvent).filter(StatusEvent.issue_id == issue_id).all()
        status_sequence = [e.next_status for e in events]
        self.assertIn("DRAFT", status_sequence)
        self.assertIn("SUBMITTED", status_sequence)
        self.assertIn("ASSIGNED", status_sequence)
        self.assertIn("IN_PROGRESS", status_sequence)
        self.assertIn("REPAIR_REPORTED", status_sequence)
        self.assertIn("RESOLVED", status_sequence)

    def test_02_separation_of_duty_blocking(self):
        """Verify rule: Worker cannot self-approve their own repair resolution."""
        # Create an issue assigned to Worker Ramesh
        org = self.db.query(Organization).first()
        gp = self.db.query(LocalityUnit).filter(LocalityUnit.official_code == "GP-KA-571434").first()
        issue = Issue(
            reference_number=f"FP-TEST-{uuid.uuid4().hex[:6]}",
            category="road_damage",
            status="REPAIR_REPORTED",
            priority="HIGH",
            organization_id=org.id,
            locality_unit_id=gp.id,
            assigned_worker_id=self.worker.id,
        )
        self.db.add(issue)
        self.db.commit()

        # Ramesh (as reviewer/worker) attempts to approve his own repair -> 403 Forbidden
        with self.assertRaises(HTTPException) as ctx:
            review_resolution(
                issue.id,
                ResolutionReviewRequest(decision="APPROVE", explanation="I did good work"),
                current_reviewer=self.worker,  # Same person
                db=self.db,
            )
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("Separation-of-Duty Violation", ctx.exception.detail)

    def test_03_duplicate_candidate_linking(self):
        """
        Verify duplicate candidate workflow (Section 1.2 & 4.3):
        - Two nearby submissions link to one physical issue.
        - Neither submission is deleted.
        - Original citizen text and tracking IDs remain completely intact.
        """
        ward = self.db.query(LocalityUnit).filter(LocalityUnit.official_code == "W1-GOWD").first()

        # Submission 1 by Citizen A
        sub1_draft = create_draft(
            DraftCreateRequest(
                category="water_leak",
                description="Drinking water pipe leaking at post office gate",
                village_name="Gowdanahalli",
                ward_name=ward.name_en,
                locality_unit_id=ward.id,
                latitude=12.5150,
                longitude=76.6250,
            ),
            self.citizen_a,
            self.db,
        )
        # Add photo & submit
        rel_path1, mime1, size1, h1 = storage_service.store_private_media(generate_test_jpeg(), "leak1.jpg")
        self.db.add(MediaAsset(profile_id=self.citizen_a.id, submission_id=sub1_draft.id, issue_id=sub1_draft.id, evidence_role="CITIZEN_BEFORE", storage_path=rel_path1, mime_type=mime1, file_size_bytes=size1, file_hash=h1, is_quarantined=True))
        self.db.commit()
        sub1 = submit_report(sub1_draft.id, SubmitReportRequest(), self.citizen_a, self.db)

        # Submission 2 by Citizen B (25m away, same problem reported independently)
        sub2_draft = create_draft(
            DraftCreateRequest(
                category="water_leak",
                description="Clean water overflowing on road near post office",
                village_name="Gowdanahalli",
                ward_name=ward.name_en,
                locality_unit_id=ward.id,
                latitude=12.5152,  # ~25m away
                longitude=76.6251,
            ),
            self.citizen_b,
            self.db,
        )
        rel_path2, mime2, size2, h2 = storage_service.store_private_media(generate_test_jpeg(), "leak2.jpg")
        self.db.add(MediaAsset(profile_id=self.citizen_b.id, submission_id=sub2_draft.id, issue_id=sub2_draft.id, evidence_role="CITIZEN_BEFORE", storage_path=rel_path2, mime_type=mime2, file_size_bytes=size2, file_hash=h2, is_quarantined=True))
        self.db.commit()
        sub2 = submit_report(sub2_draft.id, SubmitReportRequest(), self.citizen_b, self.db)

        # Reviewer checks duplicate candidates for Submission 2
        candidates = get_duplicate_candidates(sub2_draft.id, current_reviewer=self.rev_gowd, db=self.db)
        self.assertGreaterEqual(len(candidates), 1)

        # Find Issue 1 in candidates
        db_sub1_before = self.db.query(Submission).filter(Submission.id == sub1.id).first()
        matched_candidate = next((c for c in candidates if c.issue_id == db_sub1_before.issue_id), None)
        self.assertIsNotNone(matched_candidate)

        # Reviewer decides to link Submission 2 to Issue 1
        decide_res = decide_duplicate(
            DuplicateDecisionRequest(
                submission_id=sub2_draft.id,
                target_issue_id=matched_candidate.issue_id,
                decision="LINK_DUPLICATE",
                reason="Both photos show identical cracked PVC elbow at post office gate",
            ),
            current_reviewer=self.rev_gowd,
            db=self.db,
        )
        self.assertEqual(decide_res["status"], "linked")

        # Verify BOTH submissions exist in DB linked to the same physical issue
        db_sub1 = self.db.query(Submission).filter(Submission.id == sub1.id).first()
        db_sub2 = self.db.query(Submission).filter(Submission.id == sub2.id).first()
        self.assertIsNotNone(db_sub1)
        self.assertIsNotNone(db_sub2)
        self.assertEqual(db_sub1.issue_id, db_sub2.issue_id)
        self.assertNotEqual(db_sub1.id, db_sub2.id)
        self.assertNotEqual(db_sub1.tracking_id, db_sub2.tracking_id)
        # Check original descriptions are preserved
        self.assertIn("pipe leaking", db_sub1.description)
        self.assertIn("overflowing on road", db_sub2.description)

    def test_04_cross_jurisdiction_staff_access_blocked(self):
        """Verify staff in Town Municipality cannot triage issues in Gowdanahalli GP."""
        gp_gowd = self.db.query(LocalityUnit).filter(LocalityUnit.official_code == "GP-KA-571434").first()
        org = self.db.query(Organization).first()

        issue_in_gowd = Issue(
            reference_number=f"FP-TEST-{uuid.uuid4().hex[:6]}",
            category="garbage",
            status="SUBMITTED",
            priority="MEDIUM",
            organization_id=org.id,
            locality_unit_id=gp_gowd.id,
        )
        self.db.add(issue_in_gowd)
        self.db.commit()

        # Town Reviewer attempts triage -> 403 Forbidden
        with self.assertRaises(HTTPException) as ctx:
            triage_issue(
                issue_in_gowd.id,
                TriageActionRequest(
                    priority="HIGH",
                    department_id=self.dept_roads.id,
                    audit_reason="Cross-jurisdiction attempt",
                ),
                current_reviewer=self.rev_town,
                db=self.db,
            )
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("Staff jurisdiction violation", ctx.exception.detail)

    def test_05_citizen_dispute_and_reopen_workflow(self):
        """Verify citizen can dispute a resolution and issue transitions to REOPENED."""
        org = self.db.query(Organization).first()
        gp = self.db.query(LocalityUnit).filter(LocalityUnit.official_code == "GP-KA-571434").first()

        issue = Issue(
            reference_number=f"FP-TEST-{uuid.uuid4().hex[:6]}",
            category="streetlight",
            status="RESOLVED",
            priority="MEDIUM",
            organization_id=org.id,
            locality_unit_id=gp.id,
        )
        self.db.add(issue)
        self.db.flush()

        submission = Submission(
            tracking_id=issue.reference_number,
            reporter_id=self.citizen_a.id,
            issue_id=issue.id,
            category="streetlight",
            description="Dark street light pole",
        )
        self.db.add(submission)
        self.db.commit()

        # Citizen A disputes: "Light flickers and died again after 2 hours"
        dispute_res = dispute_report(
            submission.id,
            DisputeRequest(reason="Light flickered and went dark again after two hours"),
            current_user=self.citizen_a,
            db=self.db,
        )
        self.assertEqual(dispute_res["status"], "reopened")
        self.assertEqual(dispute_res["new_status"], "REOPENED")

        # Check DB
        reopened_issue = self.db.query(Issue).filter(Issue.id == issue.id).first()
        self.assertEqual(reopened_issue.status, "REOPENED")

if __name__ == "__main__":
    unittest.main()
