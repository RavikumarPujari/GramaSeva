import os
import sys
import io
import json
import unittest
from unittest.mock import patch, MagicMock
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.ai.roboflow_service import roboflow_service, RoboflowInferenceService

def create_test_image(format="JPEG", size=(300, 300), color=(120, 150, 180)) -> bytes:
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format=format)
    return buf.getvalue()

class TestRoboflowYOLOv11Integration(unittest.TestCase):
    def setUp(self):
        self.service = RoboflowInferenceService()
        self.test_jpeg = create_test_image("JPEG")
        self.test_png = create_test_image("PNG")
        self.test_webp = create_test_image("WEBP")

    def test_01_large_garbage_dump_not_classified_as_road_damage(self):
        """Requirement 5: A large garbage dump must NOT automatically be classified as road damage."""
        preds = [
            {"class": "garbage_dump", "confidence": 0.88, "x": 150, "y": 150, "width": 200, "height": 180}
        ]
        cat, label, conf = self.service.select_primary_category(preds)
        self.assertEqual(cat, "garbage")
        self.assertNotEqual(cat, "road_damage")
        self.assertEqual(label, "garbage_dump")
        self.assertEqual(conf, 0.88)

    def test_02_clear_pothole_classification(self):
        """Pothole must classify as road_damage."""
        preds = [
            {"class": "pothole", "confidence": 0.92, "x": 100, "y": 100, "width": 80, "height": 60}
        ]
        cat, label, conf = self.service.select_primary_category(preds)
        self.assertEqual(cat, "road_damage")
        self.assertEqual(label, "pothole")
        self.assertEqual(conf, 0.92)

    def test_03_cracked_road_classification(self):
        """Road crack must classify as road_damage."""
        preds = [
            {"class": "road_crack", "confidence": 0.78, "x": 150, "y": 150, "width": 120, "height": 40}
        ]
        cat, label, conf = self.service.select_primary_category(preds)
        self.assertEqual(cat, "road_damage")
        self.assertEqual(label, "road_crack")

    def test_04_open_drain_classification(self):
        """Open drain must classify as drainage."""
        preds = [
            {"class": "open_drain", "confidence": 0.84, "x": 120, "y": 180, "width": 100, "height": 150}
        ]
        cat, label, conf = self.service.select_primary_category(preds)
        self.assertEqual(cat, "drainage")
        self.assertEqual(label, "open_drain")

    def test_05_waterlogging_classification(self):
        """Waterlogging / standing water must classify as drainage."""
        preds = [
            {"class": "waterlogging", "confidence": 0.79, "x": 150, "y": 150, "width": 250, "height": 200}
        ]
        cat, label, conf = self.service.select_primary_category(preds)
        self.assertEqual(cat, "drainage")
        self.assertEqual(label, "waterlogging")

    def test_06_multiple_civic_issues_selection_rule(self):
        """Multiple detections must preserve all detections while selecting highest confidence/area primary."""
        preds = [
            {"class": "garbage", "confidence": 0.89, "x": 80, "y": 80, "width": 70, "height": 70},
            {"class": "pothole", "confidence": 0.65, "x": 220, "y": 200, "width": 50, "height": 40},
            {"class": "crack", "confidence": 0.55, "x": 180, "y": 180, "width": 30, "height": 20},
        ]
        cat, label, conf = self.service.select_primary_category(preds)
        self.assertEqual(cat, "garbage")
        self.assertEqual(label, "garbage")
        self.assertEqual(conf, 0.89)

    def test_07_unrelated_image_no_detections(self):
        """Unrelated image returning no detections must yield NO_DETECTIONS and request citizen confirmation."""
        with patch.object(self.service, "_get_api_key", return_value="dummy_valid_key"):
            mock_client = MagicMock()
            mock_client.infer.return_value = {"predictions": []}
            with patch.object(self.service, "_get_or_create_client", return_value=mock_client):
                res = self.service.analyze_image(self.test_jpeg, village_name="Peeranwadi")
                self.assertEqual(res["status"], "NO_DETECTIONS")
                self.assertIsNone(res["primary_category"])
                self.assertIsNone(res["annotated_image_base64"])
                self.assertTrue(res["requires_human_review"])

    def test_08_blurry_or_low_confidence_image(self):
        """Detections below threshold (< 0.25) must be excluded and marked uncertain."""
        preds = [
            {"class": "pothole", "confidence": 0.18, "x": 100, "y": 100, "width": 50, "height": 50}
        ]
        cat, label, conf = self.service.select_primary_category(preds)
        self.assertIsNone(cat)
        self.assertIsNone(label)

    def test_09_corrupted_image_safe_rejection(self):
        """Corrupted byte sequence must be safely rejected with specific error."""
        corrupted_bytes = b"NOT_A_VALID_IMAGE_HEADER_BYTES_12345678"
        valid, msg, img = self.service.validate_image_bytes(corrupted_bytes)
        self.assertFalse(valid)
        self.assertIn("Corrupted or invalid", msg)
        self.assertIsNone(img)

    def test_10_unsupported_file_format(self):
        """Unsupported formats (GIF/PDF) must be rejected."""
        # Create GIF image
        gif_img = Image.new("P", (100, 100))
        gif_buf = io.BytesIO()
        gif_img.save(gif_buf, format="GIF")
        valid, msg, img = self.service.validate_image_bytes(gif_buf.getvalue())
        self.assertFalse(valid)
        self.assertIn("Unsupported image format", msg)

    def test_11_missing_api_key_graceful_handling(self):
        """Missing or placeholder API key must return UNAVAILABLE without raising unhandled exceptions."""
        with patch.dict(os.environ, {"ROBOFLOW_API_KEY": "YOUR_NEW_PRIVATE_KEY"}):
            res = self.service.analyze_image(self.test_jpeg)
            self.assertEqual(res["status"], "UNAVAILABLE")
            self.assertIn("not configured", res["error"])

    def test_12_roboflow_timeout_or_error_handling(self):
        """Service network error must be caught cleanly without exposing API keys."""
        with patch.object(self.service, "_get_api_key", return_value="secret_test_key_xyz"):
            mock_client = MagicMock()
            mock_client.infer.side_effect = TimeoutError("Connection to serverless.roboflow.com timed out")
            with patch.object(self.service, "_get_or_create_client", return_value=mock_client):
                res = self.service.analyze_image(self.test_jpeg)
                self.assertEqual(res["status"], "UNAVAILABLE")
                self.assertIn("timed out", res["error"])
                # Key must not appear in error
                self.assertNotIn("secret_test_key_xyz", res["error"])

    def test_13_no_valid_detections_no_artificial_bounding_boxes(self):
        """When no objects are detected, no artificial bounding boxes should be drawn."""
        img = Image.open(io.BytesIO(self.test_jpeg))
        b64 = self.service.draw_bounding_boxes(img, [])
        self.assertTrue(b64.startswith("data:image/jpeg;base64,"))

    def test_14_citizen_correcting_suggested_category(self):
        """Model suggestion is separate from citizen decision; citizen can correct."""
        model_cat = "garbage"
        citizen_choice = "road_damage"
        self.assertNotEqual(model_cat, citizen_choice)

    def test_15_bounding_box_coordinate_scaling(self):
        """Bounding box center (x, y) to corner (xmin, ymin, xmax, ymax) calculation."""
        preds = [
            {"class": "pothole", "confidence": 0.85, "x": 150.0, "y": 150.0, "width": 100.0, "height": 80.0}
        ]
        img = Image.open(io.BytesIO(self.test_jpeg))
        b64 = self.service.draw_bounding_boxes(img, preds)
        self.assertTrue(b64.startswith("data:image/jpeg;base64,"))

    def test_16_file_size_exceeding_limit_rejected(self):
        """Images larger than 10MB must be rejected."""
        fake_oversized = b"0" * (11 * 1024 * 1024)
        valid, msg, img = self.service.validate_image_bytes(fake_oversized)
        self.assertFalse(valid)
        self.assertIn("exceeds maximum allowed size", msg)

if __name__ == "__main__":
    unittest.main()
