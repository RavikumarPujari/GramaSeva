import unittest
import sys
import os

# Add parent directory to path so app can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import root, health_check, pilot_metadata, app

class TestHealthAndMeta(unittest.TestCase):
    def test_app_metadata(self):
        self.assertEqual(app.title, "FixProof Civic API")
        self.assertEqual(app.version, "0.1.0")

    def test_root_endpoint(self):
        data = root()
        self.assertEqual(data["name"], "FixProof Civic API")
        self.assertEqual(data["version"], "0.1.0")
        self.assertEqual(data["health"], "/api/v1/health")

    def test_health_check(self):
        data = health_check()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["service"], "fixproof-api")
        self.assertIn("timestamp", data)
        self.assertEqual(data["version"], "0.1.0")

    def test_meta_endpoint(self):
        data = pilot_metadata()
        self.assertEqual(data["supported_locales"], ["en", "kn", "hi"])
        self.assertEqual(data["pilot_jurisdiction"]["state"], "Karnataka")
        self.assertEqual(data["pilot_jurisdiction"]["district"], "Belagavi District")
        self.assertGreaterEqual(len(data["supported_categories"]), 7)
        self.assertIn("RESOLVED", data["lifecycle_statuses"])
        self.assertIn("REPAIR_REPORTED", data["lifecycle_statuses"])

if __name__ == "__main__":
    unittest.main()
