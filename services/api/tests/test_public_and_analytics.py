import unittest
import uuid
import sys
import os
from datetime import datetime, timezone, timedelta

# Ensure local test environment
os.environ["DATABASE_URL"] = "sqlite:///./fixproof_dev.db"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal, Base, engine
from app.models.users import Profile, RoleAssignment
from app.models.localities import Organization, LocalityUnit, Department
from app.models.issues import (
    Issue,
    Submission,
    MediaAsset,
    StatusEvent,
    Notification,
    Feedback,
)
from app.storage.service import storage_service
from app.core.sla import compute_sla_status, get_sla_target_hours
from app.notifications.service import notification_service
from app.public.router import (
    get_public_issues,
    get_public_issue_detail,
    track_public_issue,
    view_public_media,
    get_public_analytics,
    get_public_localities,
)
from app.staff.router import approve_media_for_public, quarantine_media
from app.reports.router import submit_report_feedback, get_report_feedback
from app.notifications.router import get_user_notifications, mark_notification_read, mark_all_notifications_read
from fastapi import HTTPException

class TestPublicAndAnalytics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.db = SessionLocal()

        # Seed minimal fixtures
        cls.org = cls.db.query(Organization).first()
        if not cls.org:
            cls.org = Organization(name="Test Org", code=f"ORG-{uuid.uuid4().hex[:6]}")
            cls.db.add(cls.org)
            cls.db.flush()

        cls.reviewer = cls.db.query(Profile).filter(Profile.email.like("%reviewer%")).first()
        cls.citizen = cls.db.query(Profile).filter(Profile.email.like("%citizen%")).first()
        if not cls.citizen:
            cls.citizen = Profile(
                email=f"test.citizen.{uuid.uuid4().hex[:6]}@example.com",
                password_hash="fake",
                full_name="Test Citizen Analytics",
                preferred_locale="en",
            )
            cls.db.add(cls.citizen)
            cls.db.flush()
            cls.db.add(RoleAssignment(profile_id=cls.citizen.id, role="citizen", is_active=True))

        cls.ward = cls.db.query(LocalityUnit).filter(LocalityUnit.unit_type == "ward").first()
        cls.db.commit()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_01_public_media_access_control(self):
        """Public cannot access unapproved/quarantined media; only approved media is served."""
        from io import BytesIO
        from PIL import Image

        # 1. Create a valid test image
        buf = BytesIO()
        img = Image.new("RGB", (100, 100), color="blue")
        img.save(buf, format="JPEG")
        img_bytes = buf.getvalue()

        storage_path, mime, size_bytes, file_hash = storage_service.store_private_media(img_bytes, "test_pic.jpg")

        media = MediaAsset(
            profile_id=self.citizen.id,
            evidence_role="CITIZEN_BEFORE",
            storage_path=storage_path,
            file_hash=file_hash,
            mime_type=mime,
            file_size_bytes=size_bytes,
            is_quarantined=True,
            is_public_approved=False,
        )
        self.db.add(media)
        self.db.commit()
        self.db.refresh(media)

        # Attempt public view when quarantined/unapproved -> must raise 403 Forbidden
        with self.assertRaises(HTTPException) as cm:
            view_public_media(media_id=media.id, db=self.db)
        self.assertEqual(cm.exception.status_code, 403)

        # Moderator approves media for public
        approve_res = approve_media_for_public(
            media_id=media.id,
            current_reviewer=self.reviewer,
            db=self.db,
        )
        self.assertTrue(approve_res["is_public_approved"])

        # Public view must now succeed
        response = view_public_media(media_id=media.id, db=self.db)
        self.assertIsNotNone(response)
        self.assertEqual(response.media_type, "image/jpeg")

    def test_02_public_issue_sanitization(self):
        """Public projection strictly removes reporter personal details and generalises coordinates."""
        unique_ref = f"FP-2026-TEST-{uuid.uuid4().hex[:6]}"
        issue = Issue(
            reference_number=unique_ref,
            category="road_damage",
            status="IN_PROGRESS",
            priority="HIGH",
            organization_id=self.org.id,
            locality_unit_id=self.ward.id if self.ward else None,
            latitude=12.5234567,  # Exact residential coordinate
            longitude=76.8971234,
            public_latitude=12.523,  # Sanitized ~100m coordinate
            public_longitude=76.897,
        )
        self.db.add(issue)
        self.db.commit()
        self.db.refresh(issue)

        sub = Submission(
            tracking_id=unique_ref,
            reporter_id=self.citizen.id,
            issue_id=issue.id,
            category="road_damage",
            description="Private citizen explanation containing personal landmark info",
            locale="en",
            latitude=12.5234567,
            longitude=76.8971234,
            is_anonymous=False,
        )
        self.db.add(sub)
        self.db.commit()

        # Query public projection
        public_list = get_public_issues(
            category="road_damage",
            status_filter="IN_PROGRESS",
            limit=20,
            offset=0,
            db=self.db,
        )
        matched = next((item for item in public_list if item.reference_number == unique_ref), None)
        self.assertIsNotNone(matched)

        # Ensure generalized coordinates
        self.assertEqual(matched.public_latitude, 12.523)
        self.assertEqual(matched.public_longitude, 76.897)

        # Check detail endpoint
        detail = get_public_issue_detail(issue_id=issue.id, db=self.db)
        # Verify schema has no reporter personal attributes
        detail_dict = detail.model_dump()
        self.assertNotIn("reporter_id", detail_dict)
        self.assertNotIn("reporter_email", detail_dict)
        self.assertNotIn("reporter_name", detail_dict)
        self.assertNotIn("reporter_phone", detail_dict)
        self.assertNotIn("description", detail_dict)  # Citizen raw private text not exposed

    def test_03_accurate_public_counts_and_duplicates(self):
        """Public counts accurately distinguish unique physical issues from total citizen submissions."""
        # Create 1 physical issue
        unique_ref = f"FP-2026-COUNT-{uuid.uuid4().hex[:6]}"
        issue = Issue(
            reference_number=unique_ref,
            category="garbage_dump",
            status="SUBMITTED",
            priority="MEDIUM",
            organization_id=self.org.id,
            locality_unit_id=self.ward.id if self.ward else None,
        )
        self.db.add(issue)
        self.db.commit()

        # Link 2 distinct citizen submissions to this same physical issue (duplicate reports)
        sub1 = Submission(
            tracking_id=f"TRK-1-{uuid.uuid4().hex[:6]}",
            reporter_id=self.citizen.id,
            issue_id=issue.id,
            category="garbage_dump",
            description="Citizen 1 report of garbage pile",
            locale="en",
        )
        sub2 = Submission(
            tracking_id=f"TRK-2-{uuid.uuid4().hex[:6]}",
            reporter_id=self.citizen.id,
            issue_id=issue.id,
            category="garbage_dump",
            description="Citizen 2 report of same garbage pile",
            locale="kn",
        )
        self.db.add_all([sub1, sub2])
        self.db.commit()

        # Check analytics
        analytics = get_public_analytics(db=self.db)
        # Total submissions must be greater than or equal to total unique issues
        self.assertGreaterEqual(analytics.total_submissions, analytics.total_unique_issues)
        self.assertGreater(analytics.total_submissions, 0)
        self.assertGreater(analytics.total_unique_issues, 0)

        # Check issue summary submissions_count
        public_list = get_public_issues(category="garbage_dump", limit=50, offset=0, db=self.db)
        matched = next((item for item in public_list if item.reference_number == unique_ref), None)
        self.assertIsNotNone(matched)
        self.assertEqual(matched.submissions_count, 2)

    def test_04_idempotent_in_app_notifications(self):
        """Notifications are strictly idempotent; multiple triggers with the same dedup_key return existing."""
        test_issue_id = f"test-issue-{uuid.uuid4().hex[:8]}"
        ref_num = "FP-2026-NOTIF-TEST"

        # Dispatch first notification
        n1 = notification_service.send_notification(
            db=self.db,
            profile_id=self.citizen.id,
            event_type="SUBMISSION_RECEIVED",
            reference_number=ref_num,
            issue_id=test_issue_id,
            locale="en",
            dedup_suffix="test-run",
        )
        self.assertIsNotNone(n1)

        # Dispatch identical notification (e.g. background job retry)
        n2 = notification_service.send_notification(
            db=self.db,
            profile_id=self.citizen.id,
            event_type="SUBMISSION_RECEIVED",
            reference_number=ref_num,
            issue_id=test_issue_id,
            locale="en",
            dedup_suffix="test-run",
        )
        # Must return the same record, not a duplicate
        self.assertEqual(n1.id, n2.id)

        # Query user notifications API
        notifs_resp = get_user_notifications(current_user=self.citizen, db=self.db)
        self.assertGreater(len(notifs_resp.items), 0)
        self.assertGreaterEqual(notifs_resp.unread_count, 1)

        # Mark as read
        read_res = mark_notification_read(notification_id=n1.id, current_user=self.citizen, db=self.db)
        self.assertTrue(read_res["is_read"])

    def test_05_operational_sla_and_overdue_flags(self):
        """Operational target SLA calculation correctly flags overdue issues without statutory claims."""
        # 1. Fresh issue created 2 hours ago
        recent_time = datetime.now(timezone.utc) - timedelta(hours=2)
        fresh_sla = compute_sla_status(
            created_at=recent_time,
            category="road_damage",
            priority="HIGH",
            current_status="IN_PROGRESS",
        )
        self.assertFalse(fresh_sla["is_overdue"])
        self.assertEqual(fresh_sla["label"], "Operational Target")
        self.assertGreater(fresh_sla["hours_remaining"], 0)

        # 2. Old issue created 100 hours ago (road_damage target is 72h)
        old_time = datetime.now(timezone.utc) - timedelta(hours=100)
        overdue_sla = compute_sla_status(
            created_at=old_time,
            category="road_damage",
            priority="HIGH",
            current_status="IN_PROGRESS",
        )
        self.assertTrue(overdue_sla["is_overdue"])
        self.assertGreater(overdue_sla["overdue_by_hours"], 0)

    def test_06_citizen_feedback_submission(self):
        """Citizen can submit feedback only on resolved issues; rejected if issue is open."""
        unique_ref = f"FP-2026-FB-{uuid.uuid4().hex[:6]}"
        issue = Issue(
            reference_number=unique_ref,
            category="street_light",
            status="IN_PROGRESS",
            priority="LOW",
            organization_id=self.org.id,
        )
        self.db.add(issue)
        self.db.commit()

        sub = Submission(
            tracking_id=unique_ref,
            reporter_id=self.citizen.id,
            issue_id=issue.id,
            category="street_light",
            description="Streetlight fixture loose",
            locale="en",
        )
        self.db.add(sub)
        self.db.commit()

        from app.reports.router import FeedbackRequest
        # Attempt feedback while issue is IN_PROGRESS -> must fail with 400
        with self.assertRaises(HTTPException) as cm:
            submit_report_feedback(
                id=sub.id,
                req=FeedbackRequest(rating=5, comment="Great quick fix"),
                current_user=self.citizen,
                db=self.db,
            )
        self.assertEqual(cm.exception.status_code, 400)

        # Mark issue as RESOLVED
        issue.status = "RESOLVED"
        issue.resolved_at = datetime.now(timezone.utc)
        self.db.commit()

        # Submit feedback now -> must succeed
        fb_res = submit_report_feedback(
            id=sub.id,
            req=FeedbackRequest(rating=5, comment="Fixed cleanly and working well!"),
            current_user=self.citizen,
            db=self.db,
        )
        self.assertEqual(fb_res["status"], "created")

        # Retrieve feedback
        fb_get = get_report_feedback(id=sub.id, current_user=self.citizen, db=self.db)
        self.assertTrue(fb_get["has_feedback"])
        self.assertEqual(fb_get["rating"], 5)
        self.assertEqual(fb_get["comment"], "Fixed cleanly and working well!")

    def test_09_track_public_issue_by_tracking_id_and_reference(self):
        """Verifies track_public_issue resolves by tracking_id or reference_number and eliminates 404s."""
        test_ref = f"GS-2026-BEL-{uuid.uuid4().hex[:4].upper()}"
        issue = Issue(
            reference_number=test_ref,
            category="water_leakage",
            status="SUBMITTED",
            priority="HIGH",
            organization_id=self.org.id,
            latitude=15.8152,
            longitude=74.4610,
        )
        self.db.add(issue)
        self.db.flush()

        sub = Submission(
            tracking_id=test_ref,
            reporter_id=self.citizen.id,
            issue_id=issue.id,
            category="water_leakage",
            description="Major pipeline leak near village square",
            locale="en",
        )
        self.db.add(sub)
        self.db.commit()

        # Track by reference_number / tracking_id -> must succeed
        tracked = track_public_issue(reference_number=test_ref, db=self.db)
        self.assertIsNotNone(tracked)
        self.assertEqual(tracked.reference_number, test_ref)
        self.assertEqual(tracked.status, "SUBMITTED")
        self.assertEqual(tracked.category, "water_leakage")

        # Track by Issue UUID -> must also succeed
        tracked_by_uuid = track_public_issue(reference_number=issue.id, db=self.db)
        self.assertEqual(tracked_by_uuid.reference_number, test_ref)

        # get_public_issue_detail with reference_number -> must also succeed
        detail_by_ref = get_public_issue_detail(issue_id=test_ref, db=self.db)
        self.assertEqual(detail_by_ref.id, issue.id)

        # Invalid reference -> must raise 404
        with self.assertRaises(HTTPException) as cm:
            track_public_issue(reference_number="NONEXISTENT-ID-9999", db=self.db)
        self.assertEqual(cm.exception.status_code, 404)

if __name__ == "__main__":
    unittest.main()
