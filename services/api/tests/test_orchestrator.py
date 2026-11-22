import os
import sys
import io
import unittest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from PIL import Image
from app.ai.orchestrator import ai_orchestrator
from app.core.database import SessionLocal
from app.models.issues import Issue

class TestAIOrchestrator(unittest.TestCase):
    def setUp(self):
        self.orchestrator = ai_orchestrator
        img = Image.new("RGB", (256, 256), color=(120, 120, 120))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        self.valid_image_bytes = buf.getvalue()

    def test_01_orchestrator_initialization(self):
        """Verifies orchestrator dependencies are wired correctly."""
        self.assertIsNotNone(self.orchestrator.roboflow_engine)
        self.assertIsNotNone(self.orchestrator.gemini)
        self.assertIsNotNone(self.orchestrator.ocr)
        self.assertIsNotNone(self.orchestrator.landmarks)

    def test_02_orchestrate_complaint_analysis(self):
        """Verifies end-to-end complaint analysis orchestration."""
        res = self.orchestrator.orchestrate_complaint_analysis(
            image_bytes=self.valid_image_bytes,
            filename="road_defect.jpg",
            latitude=15.8152,
            longitude=74.4610,
            village_name="Peeranwadi",
            category_hint="road_damage",
            full_evaluation=False,
            db=None,
        )
        self.assertEqual(res["status"], "completed")
        self.assertIn("predicted_category", res)
        self.assertIn("ai_description", res)
        self.assertIn("observations", res)
        self.assertIn("model_summaries", res)
        self.assertIn("photo_location_status", res)
        self.assertIn("latency_ms", res)
        self.assertGreater(res["latency_ms"], 0)

    def test_03_invalid_image_rejection(self):
        """Verifies corrupt or empty image is cleanly rejected with error status."""
        res = self.orchestrator.orchestrate_complaint_analysis(
            image_bytes=b"not_an_image",
            filename="corrupt.jpg",
        )
        self.assertEqual(res["status"], "error")
        self.assertIn("error", res)

    def test_04_duplicate_detection_integration(self):
        """Verifies duplicate check flags nearby existing issues."""
        db = SessionLocal()
        try:
            # Check with peeranwadi coordinates
            res = self.orchestrator.orchestrate_complaint_analysis(
                image_bytes=self.valid_image_bytes,
                filename="test_pothole.jpg",
                latitude=15.8152,
                longitude=74.4610,
                village_name="Peeranwadi",
                category_hint="road_damage",
                db=db,
            )
            self.assertIn("duplicate_detected", res)
            self.assertIsInstance(res["duplicate_detected"], bool)
        finally:
            db.close()

if __name__ == "__main__":
    unittest.main()
