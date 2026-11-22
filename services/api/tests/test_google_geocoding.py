import io
import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock

# Configure ultralytics config dir within project to avoid permissions issue
os.environ["YOLO_CONFIG_DIR"] = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".ultralytics"))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from app.core.database import SessionLocal
from app.models import Profile, Submission, Issue
from app.localities.router import google_geocode_endpoint
from app.reports.router import create_draft, DraftCreateRequest
from database.seeds.demo_seed import seed_database

SAMPLE_GOOGLE_RESPONSE = {
    "status": "OK",
    "results": [
        {
            "place_id": "ChIJ_peeranwadi_sample_place_id",
            "formatted_address": "Peeranwadi, Belagavi, Karnataka 590014, India",
            "address_components": [
                {"long_name": "Peeranwadi", "short_name": "Peeranwadi", "types": ["sublocality_level_1", "sublocality", "political"]},
                {"long_name": "Belagavi", "short_name": "Belagavi", "types": ["locality", "political"]},
                {"long_name": "Belagavi Taluk", "short_name": "Belagavi Taluk", "types": ["administrative_area_level_3", "political"]},
                {"long_name": "Belagavi District", "short_name": "Belagavi", "types": ["administrative_area_level_2", "political"]},
                {"long_name": "Karnataka", "short_name": "KA", "types": ["administrative_area_level_1", "political"]},
                {"long_name": "India", "short_name": "IN", "types": ["country", "political"]},
                {"long_name": "590014", "short_name": "590014", "types": ["postal_code"]},
            ]
        }
    ]
}

SAMPLE_NO_VILLAGE_RESPONSE = {
    "status": "OK",
    "results": [
        {
            "place_id": "ChIJ_remote_spot_place_id",
            "formatted_address": "State Highway 12, Karnataka, India",
            "address_components": [
                {"long_name": "State Highway 12", "short_name": "SH 12", "types": ["route"]},
                {"long_name": "Belagavi District", "short_name": "Belagavi", "types": ["administrative_area_level_2", "political"]},
                {"long_name": "Karnataka", "short_name": "KA", "types": ["administrative_area_level_1", "political"]},
                {"long_name": "India", "short_name": "IN", "types": ["country", "political"]},
            ]
        }
    ]
}

class TestGoogleGeocodingIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed_database()
        cls.db = SessionLocal()
        cls.citizen = cls.db.query(Profile).filter(Profile.email == "citizen.ananya@example.com").first()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    @patch("app.localities.router.urllib.request.urlopen")
    def test_01_google_geocode_extracts_components(self, mock_urlopen):
        """Verifies google_geocode_endpoint extracts real address components from Google Maps response."""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps(SAMPLE_GOOGLE_RESPONSE).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        res = google_geocode_endpoint(latitude=15.8152, longitude=74.4610)
        self.assertEqual(res.village, "Peeranwadi")
        self.assertEqual(res.taluk, "Belagavi Taluk")
        self.assertEqual(res.district, "Belagavi District")
        self.assertEqual(res.state, "Karnataka")
        self.assertEqual(res.country, "India")
        self.assertEqual(res.postal_code, "590014")
        self.assertEqual(res.place_id, "ChIJ_peeranwadi_sample_place_id")
        self.assertEqual(res.provider, "google_maps")
        self.assertEqual(res.geocoding_status, "OK")

    @patch("app.localities.router.urllib.request.urlopen")
    def test_02_honest_missing_village_and_taluk_handling(self, mock_urlopen):
        """Verifies missing village and taluk return explicit unavailable message without fabricating."""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps(SAMPLE_NO_VILLAGE_RESPONSE).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        res = google_geocode_endpoint(latitude=15.8500, longitude=74.5000)
        self.assertEqual(res.village, "Village not available from Google Maps response")
        self.assertEqual(res.taluk, "Taluk not available from Google Maps response")
        self.assertEqual(res.state, "Karnataka")
        self.assertEqual(res.district, "Belagavi District")

    def test_03_create_draft_with_google_geocoding_metadata(self):
        """Verifies complaint creation persists Google geocoded location components into PostgreSQL/SQLite."""
        req = DraftCreateRequest(
            category="road_damage",
            description="Deep pothole reported near Peeranwadi highway junction.",
            latitude=15.8152,
            longitude=74.4610,
            gps_accuracy=10.5,
            location_method="GPS_VERIFIED",
            confirmed_latitude=15.8152,
            confirmed_longitude=74.4610,
            confirmed_address="Peeranwadi, Belagavi, Karnataka 590014, India",
            detected_village="Peeranwadi",
            detected_taluk="Belagavi Taluk",
            detected_district="Belagavi District",
            detected_state="Karnataka",
            detected_country="India",
            detected_postal_code="590014",
            google_place_id="ChIJ_peeranwadi_sample_place_id",
            geocoding_status="OK",
            location_confirmation_status="CITIZEN_CONFIRMED",
        )

        resp = create_draft(req=req, current_user=self.citizen, db=self.db)
        self.assertIsNotNone(resp.tracking_id)
        self.assertTrue(resp.tracking_id.startswith("GS-"))
        self.assertEqual(resp.detected_village, "Peeranwadi")
        self.assertEqual(resp.detected_taluk, "Belagavi Taluk")
        self.assertEqual(resp.detected_district, "Belagavi District")
        self.assertEqual(resp.detected_state, "Karnataka")
        self.assertEqual(resp.detected_country, "India")
        self.assertEqual(resp.detected_postal_code, "590014")
        self.assertEqual(resp.google_place_id, "ChIJ_peeranwadi_sample_place_id")
        self.assertEqual(resp.geocoding_status, "OK")
        self.assertEqual(resp.location_confirmation_status, "CITIZEN_CONFIRMED")

        # Directly verify database record persistence
        persisted = self.db.query(Submission).filter(Submission.tracking_id == resp.tracking_id).first()
        self.assertIsNotNone(persisted)
        self.assertEqual(persisted.detected_village, "Peeranwadi")
        self.assertEqual(persisted.detected_taluk, "Belagavi Taluk")
        self.assertEqual(persisted.detected_district, "Belagavi District")
        self.assertEqual(persisted.google_place_id, "ChIJ_peeranwadi_sample_place_id")
        self.assertEqual(persisted.location_confirmation_status, "CITIZEN_CONFIRMED")

if __name__ == "__main__":
    unittest.main()
