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
from app.models import Profile, Submission, Issue, MediaAsset
from app.storage.service import storage_service
from app.reports.router import (
    create_draft,
    update_draft,
    submit_report,
    get_report_detail,
    list_my_reports,
    DraftCreateRequest,
    DraftUpdateRequest,
    SubmitReportRequest,
)
from database.seeds.demo_seed import seed_database

def generate_test_jpeg(width=120, height=120) -> bytes:
    buffer = BytesIO()
    img = Image.new("RGB", (width, height), color=(200, 50, 50))
    img.save(buffer, format="JPEG")
    return buffer.getvalue()

def generate_test_png(width=100, height=100) -> bytes:
    buffer = BytesIO()
    img = Image.new("RGB", (width, height), color=(50, 150, 250))
    img.save(buffer, format="PNG")
    return buffer.getvalue()

class TestCitizenReportingAndMedia(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed_database()
        cls.db = SessionLocal()
        cls.citizen_a = cls.db.query(Profile).filter(Profile.email == "citizen.ananya@example.com").first()
        cls.citizen_b = cls.db.query(Profile).filter(Profile.email == "citizen.suresh@example.com").first()
        cls.reviewer = cls.db.query(Profile).filter(Profile.email == "reviewer.gowdanahalli@fixproof.org").first()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_01_media_security_validation(self):
        """Verify strict magic bytes and decodability validation."""
        # 1. Valid JPEG is accepted
        valid_jpeg = generate_test_jpeg()
        mime, ext, size, f_hash = storage_service.validate_and_inspect_media(valid_jpeg, "pothole.jpg")
        self.assertEqual(mime, "image/jpeg")
        self.assertEqual(ext, ".jpg")
        self.assertGreater(size, 0)
        self.assertEqual(len(f_hash), 64)

        # 2. Valid PNG is accepted
        valid_png = generate_test_png()
        mime_png, ext_png, _, _ = storage_service.validate_and_inspect_media(valid_png, "drainage.png")
        self.assertEqual(mime_png, "image/png")
        self.assertEqual(ext_png, ".png")

        # 3. Disguised text file (fake extension) is REJECTED
        fake_image = b"This is a text file pretending to be an image.jpg"
        with self.assertRaises(HTTPException) as ctx:
            storage_service.validate_and_inspect_media(fake_image, "fake.jpg")
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Invalid file signature", ctx.exception.detail)

        # 4. Empty file is REJECTED
        with self.assertRaises(HTTPException) as ctx:
            storage_service.validate_and_inspect_media(b"", "empty.jpg")
        self.assertEqual(ctx.exception.status_code, 400)

        # 5. Corrupt header is REJECTED
        corrupt_jpeg = b"\xff\xd8\xff" + b"CorruptGarbageDataNotAnImage"
        with self.assertRaises(HTTPException) as ctx:
            storage_service.validate_and_inspect_media(corrupt_jpeg, "corrupt.jpg")
        self.assertEqual(ctx.exception.status_code, 400)

    def test_02_draft_creation_and_update(self):
        """Verify citizen can create a draft and update it before submission."""
        draft_req = DraftCreateRequest(
            category="road_damage",
            description="Deep pothole near the old bridge",
            village_name="Gowdanahalli",
            ward_name=None,  # Ward unknown
            latitude=12.512,
            longitude=76.621,
        )
        report = create_draft(draft_req, self.citizen_a, self.db)
        self.assertIsNotNone(report.id)
        self.assertTrue(report.tracking_id.startswith("GS-") or report.tracking_id.startswith("FP-"))
        self.assertEqual(report.status, "DRAFT")
        self.assertEqual(report.category, "road_damage")
        self.assertIsNone(report.ward_name)

        # Update draft description
        update_req = DraftUpdateRequest(
            description="Updated: Deep pothole near the old bridge, causing accidents at night.",
            ward_name="Ward 1 (Post Office)",
        )
        updated = update_draft(report.id, update_req, self.citizen_a, self.db)
        self.assertIn("Updated", updated.description)
        self.assertEqual(updated.ward_name, "Ward 1 (Post Office)")

    def test_03_submission_requires_evidence(self):
        """Verify submitting without evidence photo is blocked."""
        draft_req = DraftCreateRequest(category="garbage", description="Litter on street")
        draft = create_draft(draft_req, self.citizen_a, self.db)

        # Attempt to submit without media
        submit_req = SubmitReportRequest()
        with self.assertRaises(HTTPException) as ctx:
            submit_report(draft.id, submit_req, self.citizen_a, self.db)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Evidence photo is required", ctx.exception.detail)

    def test_04_successful_submission_with_ward_unknown(self):
        """Verify complaint submission succeeds with photo evidence even if ward is unknown."""
        draft_req = DraftCreateRequest(
            category="water_leak",
            description="Continuous leakage from main pipeline",
            village_name="Gowdanahalli",
            ward_name="unknown",
            latitude=12.515,
            longitude=76.624,
        )
        draft = create_draft(draft_req, self.citizen_a, self.db)

        # Attach real photo evidence directly to test storage
        img_bytes = generate_test_jpeg(200, 200)
        rel_path, mime, size, f_hash = storage_service.store_private_media(img_bytes, "leak.jpg")
        media = MediaAsset(
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
        self.db.add(media)
        self.db.commit()

        # Submit
        submitted = submit_report(draft.id, SubmitReportRequest(), self.citizen_a, self.db)
        self.assertEqual(submitted.status, "SUBMITTED")
        self.assertEqual(len(submitted.media_assets), 1)
        self.assertEqual(submitted.media_assets[0].evidence_role, "CITIZEN_BEFORE")
        self.assertGreaterEqual(len(submitted.timeline), 2)  # DRAFT -> SUBMITTED

        # Test idempotency: re-submitting returns the same record without error
        resubmit = submit_report(draft.id, SubmitReportRequest(), self.citizen_a, self.db)
        self.assertEqual(resubmit.status, "SUBMITTED")
        self.assertEqual(resubmit.tracking_id, submitted.tracking_id)

    def test_05_privacy_cross_citizen_access_blocked(self):
        """
        Verify privacy rule (Section 13.1):
        Citizen B cannot view Citizen A's private report or evidence.
        """
        draft_req = DraftCreateRequest(category="streetlight", description="Private issue")
        report_a = create_draft(draft_req, self.citizen_a, self.db)

        # Citizen B attempts to access Citizen A's report -> 403 Forbidden
        with self.assertRaises(HTTPException) as ctx:
            get_report_detail(report_a.id, self.citizen_b, self.db)
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("Access forbidden", ctx.exception.detail)

        # Reviewer CAN access for triage purposes
        staff_view = get_report_detail(report_a.id, self.reviewer, self.db)
        self.assertEqual(staff_view.id, report_a.id)

if __name__ == "__main__":
    unittest.main()
