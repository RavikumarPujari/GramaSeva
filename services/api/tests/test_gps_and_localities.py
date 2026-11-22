import unittest
import sys
import os
from io import BytesIO
from PIL import Image
from starlette.datastructures import UploadFile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from app.core.database import SessionLocal
from app.models import Issue, Submission, Profile, MediaAsset
from app.storage.service import storage_service
from app.localities.router import (
    resolve_gps_get,
    resolve_gps_post,
    ResolveGPSRequest,
)
from app.reports.router import (
    create_draft,
    submit_report,
    DraftCreateRequest,
    SubmitReportRequest,
)
from database.seeds.demo_seed import seed_database

def generate_test_jpeg() -> bytes:
    buf = BytesIO()
    img = Image.new("RGB", (128, 128), color=(30, 140, 200))
    img.save(buf, format="JPEG")
    return buf.getvalue()

class TestGPSAndLocalities(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed_database()
        cls.db = SessionLocal()
        cls.citizen = cls.db.query(Profile).filter(Profile.email == "citizen.ananya@example.com").first()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_01_resolve_gps_peeranwadi_success(self):
        """resolve_gps_get correctly identifies Peeranwadi within verified pilot boundary."""
        res = resolve_gps_get(latitude=15.8152, longitude=74.4610, db=self.db)
        self.assertTrue(res.is_verified)
        self.assertEqual(res.village_name, "Peeranwadi")
        self.assertEqual(res.taluk, "Belagavi Taluk")
        self.assertEqual(res.district, "Belagavi District")
        self.assertLessEqual(res.distance_km, 0.1)
        self.assertTrue(res.allow_manual_selection)

    def test_02_resolve_gps_kuttalawadi_post_success(self):
        """resolve_gps_post correctly identifies Kuttalawadi via request schema."""
        req = ResolveGPSRequest(latitude=15.8280, longitude=74.4320)
        res = resolve_gps_post(req=req, db=self.db)
        self.assertTrue(res.is_verified)
        self.assertEqual(res.village_name, "Kuttalawadi")
        self.assertEqual(res.gram_panchayat, "Kuttalawadi Gram Panchayat")

    def test_03_resolve_gps_outside_pilot_fallback(self):
        """Coordinates outside Belagavi Taluk (>7km) return is_verified=False with manual fallback."""
        # Bengaluru coordinates (12.9716, 77.5946)
        res = resolve_gps_get(latitude=12.9716, longitude=77.5946, db=self.db)
        self.assertFalse(res.is_verified)
        self.assertIsNone(res.village_name)
        self.assertTrue(res.allow_manual_selection)
        self.assertIn("outside verified Belagavi pilot villages", res.message)

    def test_04_resolve_gps_all_nine_villages_verified(self):
        """All 9 official Belagavi Taluk villages resolve to their verified jurisdiction."""
        villages = [
            ("Peeranwadi", 15.8152, 74.4610),
            ("Kuttalawadi", 15.8280, 74.4320),
            ("Zad-Shahapur", 15.8360, 74.5210),
            ("Santibastawad", 15.7950, 74.4420),
            ("Yellur", 15.7720, 74.5120),
            ("Sulge (Yellur)", 15.7610, 74.4980),
            ("Mandoli", 15.8380, 74.4650),
            ("Waghawade", 15.8210, 74.4250),
            ("Navage", 15.8080, 74.4390),
        ]
        for name, lat, lon in villages:
            res = resolve_gps_get(latitude=lat, longitude=lon, db=self.db)
            self.assertTrue(res.is_verified, f"Failed for {name}")
            self.assertEqual(res.village_name, name)
            self.assertEqual(res.taluk, "Belagavi Taluk")

    def test_05_complaint_submission_stores_exact_gps_coordinates(self):
        """Complaint submission stores exact GPS latitude, longitude, accuracy and method in PostgreSQL."""
        draft_req = DraftCreateRequest(
            category="road_damage",
            description="Hazardous pothole on Peeranwadi Bypass",
            village_name="Peeranwadi",
            ward_name="Ward 3",
            taluk_name="Belagavi Taluk",
            latitude=15.815250,
            longitude=74.461050,
            reporter_name="Kavita Patil",
            reporter_phone="9876543210",
            is_guest=True,
            location_method="GPS_VERIFIED",
            gps_accuracy=14.5,
            voice_transcription="Hazardous road defect near Peeranwadi",
            ai_category_suggestion="road_damage",
            ai_confidence=0.94,
        )

        draft = create_draft(draft_req, self.citizen, self.db)
        self.assertIsNotNone(draft.id)
        self.assertTrue(draft.tracking_id.startswith("GS-"))

        # Attach real photographic evidence
        img_bytes = generate_test_jpeg()
        rel_path, mime, size, f_hash = storage_service.store_private_media(img_bytes, "pothole.jpg")
        media = MediaAsset(
            profile_id=self.citizen.id,
            submission_id=draft.id,
            issue_id=self.db.query(Submission).filter(Submission.id == draft.id).first().issue_id,
            evidence_role="CITIZEN_BEFORE",
            storage_path=rel_path,
            mime_type=mime,
            file_size_bytes=size,
            file_hash=f_hash,
            is_quarantined=False,
        )
        self.db.add(media)
        self.db.commit()

        # Submit report
        submitted = submit_report(draft.id, SubmitReportRequest(), self.citizen, self.db)
        self.assertEqual(submitted.status, "SUBMITTED")

        # Verify database record persistence
        submission = self.db.query(Submission).filter(Submission.tracking_id == draft.tracking_id).first()
        self.assertIsNotNone(submission)
        self.assertAlmostEqual(submission.latitude, 15.815250, places=4)
        self.assertAlmostEqual(submission.longitude, 74.461050, places=4)
        self.assertEqual(submission.location_method, "GPS_VERIFIED")
        self.assertAlmostEqual(submission.gps_accuracy, 14.5, places=1)
        self.assertEqual(submission.village_name, "Peeranwadi")

        issue = self.db.query(Issue).filter(Issue.reference_number == draft.tracking_id).first()
        self.assertIsNotNone(issue)
        self.assertAlmostEqual(issue.latitude, 15.815250, places=4)
        self.assertAlmostEqual(issue.longitude, 74.461050, places=4)

    def test_06_roboflow_5_models_status(self):
        """get_ai_models_status returns status summary of all 5 Roboflow models."""
        from app.ai.router import get_ai_models_status
        models = get_ai_models_status()
        self.assertEqual(len(models), 5)
        keys = [m["key"] for m in models]
        self.assertIn("garbage", keys)
        self.assertIn("road", keys)
        self.assertIn("waterlogging", keys)
        self.assertIn("civic_1", keys)
        self.assertIn("civic_2", keys)

    def test_07_verified_landmarks_registry(self):
        """list_landmarks returns the 9 official Belagavi pilot landmarks."""
        from app.localities.router import list_landmarks
        lms = list_landmarks()
        self.assertEqual(len(lms), 9)
        names = [l.name for l in lms]
        self.assertIn("Peeranwadi Gram Panchayat Bhavan", names)
        self.assertIn("Kuttalawadi Community Water Tank & Primary School", names)
        for lm in lms:
            self.assertIsNotNone(lm.latitude)
            self.assertIsNotNone(lm.longitude)
            self.assertIsNotNone(lm.verification_source)

    def test_08_verified_boundaries_registry(self):
        """list_boundaries returns 9 Belagavi Taluk pilot village boundary polygons."""
        from app.localities.router import list_boundaries
        bnds = list_boundaries()
        self.assertEqual(len(bnds), 9)
        names = [b.name_en for b in bnds]
        self.assertIn("Peeranwadi", names)
        self.assertIn("Yellur", names)
        self.assertIn("Mandoli", names)

    def test_09_dual_source_location_verification(self):
        """verify_dual_source evaluates GPS coordinates against pilot boundaries and photo clues."""
        from app.localities.router import verify_dual_source, DualSourceVerifyRequest
        req = DualSourceVerifyRequest(
            latitude=15.8152,
            longitude=74.4610,
            gps_accuracy=10.0,
            acquisition_method="GPS_VERIFIED",
            selected_village="Peeranwadi"
        )
        report = verify_dual_source(req)
        self.assertTrue(report["is_boundary_verified"])
        self.assertEqual(report["verified_village"], "Peeranwadi")
        self.assertEqual(report["jurisdiction_status"], "VERIFIED")
        self.assertEqual(report["overall_status"], "VERIFIED_GPS_ONLY")
        self.assertFalse(report["requires_pdo_review"])

    def test_10_draft_persistence_with_confirmed_location_and_ocr(self):
        """create_draft persists confirmed coordinates, ocr text, and landmark metadata."""
        req = DraftCreateRequest(
            category="garbage",
            description="Garbage pile near landmark",
            village_name="Peeranwadi",
            latitude=15.8152,
            longitude=74.4610,
            confirmed_latitude=15.81525,
            confirmed_longitude=74.46105,
            confirmed_village="Peeranwadi",
            confirmed_address="Peeranwadi Main Circle",
            confirmation_method="GPS_AND_CITIZEN_CONFIRMED",
            jurisdiction_status="VERIFIED",
            ocr_extracted_text="ಪೀರನವಾಡಿ Peeranwadi Gram Panchayat",
            photo_location_status="PHOTO_CLUES_FOUND"
        )
        draft = create_draft(req, self.citizen, self.db)
        self.assertEqual(draft.confirmed_village, "Peeranwadi")
        self.assertAlmostEqual(draft.confirmed_latitude, 15.81525, places=4)
        self.assertEqual(draft.photo_location_status, "PHOTO_CLUES_FOUND")
        self.assertEqual(draft.jurisdiction_status, "VERIFIED")

if __name__ == "__main__":
    unittest.main()
