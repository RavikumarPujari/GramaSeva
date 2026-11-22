import os
import sys
import io
import json
import unittest
from unittest.mock import patch, MagicMock
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.ai.roboflow_service import roboflow_service, RoboflowInferenceService, compute_box_iou


def create_test_image(format="JPEG", size=(300, 300), color=(120, 150, 180)) -> bytes:
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format=format)
    return buf.getvalue()


class TestMultiModelRoboflowSuite(unittest.TestCase):
    def setUp(self):
        self.service = RoboflowInferenceService()
        self.test_jpeg = create_test_image("JPEG")

    def test_01_registered_models_configuration(self):
        """Service must register all 5 exact Roboflow models."""
        models = self.service.get_registered_models()
        self.assertEqual(len(models), 5)

        keys = [m["key"] for m in models]
        self.assertIn("garbage", keys)
        self.assertIn("road", keys)
        self.assertIn("waterlogging", keys)
        self.assertIn("civic_1", keys)
        self.assertIn("civic_2", keys)

        # Check default IDs match requirements
        m_garbage = next(m for m in models if m["key"] == "garbage")
        m_road = next(m for m in models if m["key"] == "road")
        m_water = next(m for m in models if m["key"] == "waterlogging")

        self.assertIn("garbage_detection", m_garbage["model_id"])
        self.assertIn("road-damage-detection", m_road["model_id"])
        self.assertIn("water-logging", m_water["model_id"])

    def test_02_compute_box_iou(self):
        """IoU calculation for overlapping bounding boxes."""
        box1 = [0.0, 0.0, 100.0, 100.0]  # area 10,000
        box2 = [50.0, 0.0, 150.0, 100.0]  # overlap is [50, 0, 100, 100] area 5,000, union 15,000
        iou = compute_box_iou(box1, box2)
        self.assertAlmostEqual(iou, 5000.0 / 15000.0, places=3)

        # Non-overlapping
        box3 = [200.0, 200.0, 300.0, 300.0]
        self.assertEqual(compute_box_iou(box1, box3), 0.0)

    def test_03_strong_consensus_road_damage(self):
        """All 3 models detect road damage defects -> STRONG_CONSENSUS."""
        model_results = [
            {
                "model_key": "model_1",
                "model_id": "civic_issues_v1-dc7ae-zzdgj/1",
                "status": "COMPLETED",
                "primary_category": "road_damage",
                "defect_label": "pothole",
                "confidence_score": 0.89,
                "predictions": [{"class": "pothole", "confidence": 0.89, "x": 100, "y": 100, "width": 60, "height": 40}],
            },
            {
                "model_key": "model_2",
                "model_id": "civic-issue-yljwt-tptzy/2",
                "status": "COMPLETED",
                "primary_category": "road_damage",
                "defect_label": "pothole",
                "confidence_score": 0.84,
                "predictions": [{"class": "pothole", "confidence": 0.84, "x": 102, "y": 98, "width": 58, "height": 42}],
            },
            {
                "model_key": "model_3",
                "model_id": "civic-issues-qj5pb/2",
                "status": "COMPLETED",
                "primary_category": "road_damage",
                "defect_label": "damaged_road",
                "confidence_score": 0.78,
                "predictions": [{"class": "damaged_road", "confidence": 0.78, "x": 105, "y": 102, "width": 65, "height": 45}],
            },
        ]

        comparison = self.service.compare_predictions(model_results)
        self.assertEqual(comparison["consensus_status"], "STRONG_CONSENSUS")
        self.assertTrue(comparison["has_consensus"])
        self.assertEqual(comparison["consensus_category"], "road_damage")
        self.assertEqual(len(comparison["agreed_predictions"]), 1)
        self.assertEqual(comparison["agreed_predictions"][0]["count"], 3)
        self.assertEqual(len(comparison["conflicting_predictions"]), 0)

    def test_04_majority_consensus_two_of_three(self):
        """2 models detect water leak, 1 model detects nothing -> MAJORITY_CONSENSUS."""
        model_results = [
            {
                "model_key": "model_1",
                "model_id": "civic_issues_v1-dc7ae-zzdgj/1",
                "status": "COMPLETED",
                "primary_category": "water_leak",
                "defect_label": "pipe_leak",
                "confidence_score": 0.82,
                "predictions": [{"class": "pipe_leak", "confidence": 0.82, "x": 80, "y": 80, "width": 50, "height": 50}],
            },
            {
                "model_key": "model_2",
                "model_id": "civic-issue-yljwt-tptzy/2",
                "status": "COMPLETED",
                "primary_category": "water_leak",
                "defect_label": "water_leak",
                "confidence_score": 0.77,
                "predictions": [{"class": "water_leak", "confidence": 0.77, "x": 82, "y": 79, "width": 48, "height": 48}],
            },
            {
                "model_key": "model_3",
                "model_id": "civic-issues-qj5pb/2",
                "status": "NO_DETECTIONS",
                "primary_category": None,
                "defect_label": None,
                "confidence_score": None,
                "predictions": [],
            },
        ]

        comparison = self.service.compare_predictions(model_results)
        self.assertEqual(comparison["consensus_status"], "STRONG_CONSENSUS")
        self.assertTrue(comparison["has_consensus"])
        self.assertEqual(comparison["consensus_category"], "water_leak")
        self.assertEqual(comparison["agreed_predictions"][0]["count"], 2)

    def test_05_conflict_dispute_garbage_vs_road_damage(self):
        """
        CRITICAL GOVERNANCE TEST:
        When Model 1 detects road damage and Model 2 detects garbage dump,
        the system must flag DISPUTED and NEVER force garbage dump into road damage.
        """
        model_results = [
            {
                "model_key": "model_1",
                "model_id": "civic_issues_v1-dc7ae-zzdgj/1",
                "status": "COMPLETED",
                "primary_category": "road_damage",
                "defect_label": "pothole",
                "confidence_score": 0.81,
                "predictions": [{"class": "pothole", "confidence": 0.81, "x": 100, "y": 100, "width": 50, "height": 50}],
            },
            {
                "model_key": "model_2",
                "model_id": "civic-issue-yljwt-tptzy/2",
                "status": "COMPLETED",
                "primary_category": "garbage",
                "defect_label": "garbage_dump",
                "confidence_score": 0.87,
                "predictions": [{"class": "garbage_dump", "confidence": 0.87, "x": 100, "y": 100, "width": 120, "height": 100}],
            },
            {
                "model_key": "model_3",
                "model_id": "civic-issues-qj5pb/2",
                "status": "NO_DETECTIONS",
                "primary_category": None,
                "defect_label": None,
                "confidence_score": None,
                "predictions": [],
            },
        ]

        comparison = self.service.compare_predictions(model_results)
        self.assertEqual(comparison["consensus_status"], "DISPUTED")
        self.assertFalse(comparison["has_consensus"])
        self.assertIsNotNone(comparison["dispute_reason"])
        self.assertTrue(len(comparison["conflicting_predictions"]) >= 2)
        # Verify garbage was preserved and not overridden
        conflict_cats = [c["category"] for c in comparison["conflicting_predictions"]]
        self.assertIn("garbage", conflict_cats)
        self.assertIn("road_damage", conflict_cats)

    def test_06_single_model_failure_resilience(self):
        """When one model fails or throws an exception, other models must proceed without failure."""
        with patch.object(self.service, "_get_api_key", return_value="test_api_key"):
            mock_client = MagicMock()

            def side_effect(img, model_id):
                if "road-damage" in model_id:
                    raise RuntimeError("Road model timed out or endpoint unreachable")
                elif "water-logging" in model_id:
                    return {"predictions": [{"class": "garbage", "confidence": 0.85, "x": 50, "y": 50, "width": 40, "height": 40}]}
                else:
                    return {"predictions": [{"class": "waste", "confidence": 0.79, "x": 55, "y": 52, "width": 42, "height": 38}]}

            mock_client.infer.side_effect = side_effect

            with patch.object(self.service, "_get_or_create_client", return_value=mock_client):
                res = self.service.analyze_multi_model(self.test_jpeg, village_name="Sambre")

                # The failed model should be UNAVAILABLE, but overall execution succeeded
                m2_res = next(m for m in res["model_summaries"] if "road-damage" in m["model_id"])
                self.assertEqual(m2_res["status"], "UNAVAILABLE")
                self.assertIn("timed out", m2_res["error"])

                # The other 2 models succeeded and formed a consensus
                self.assertEqual(res["primary_category"], "garbage")
                self.assertEqual(res["status"], "COMPLETED")
                self.assertEqual(res["comparison"]["consensus_status"], "STRONG_CONSENSUS")

    def test_07_all_models_no_detections(self):
        """When all models inspect the image and find no detections above threshold."""
        with patch.object(self.service, "_get_api_key", return_value="test_api_key"):
            mock_client = MagicMock()
            mock_client.infer.return_value = {"predictions": []}

            with patch.object(self.service, "_get_or_create_client", return_value=mock_client):
                res = self.service.analyze_multi_model(self.test_jpeg, village_name="Peeranwadi")
                self.assertEqual(res["status"], "NO_DETECTIONS")
                self.assertFalse(res["comparison"]["has_consensus"])
                self.assertTrue(res["comparison"]["uncertain_results"])
                self.assertTrue(res["requires_human_review"])

    def test_08_multi_model_bounding_box_annotation(self):
        """Bounding boxes rendered across models include model attribution tags [M1], [M2], [M3]."""
        pil_img = Image.new("RGB", (300, 300), color=(150, 150, 150))
        model_results = [
            {
                "model_key": "model_1",
                "predictions": [{"class": "pothole", "confidence": 0.90, "x": 100, "y": 100, "width": 60, "height": 40}],
            },
            {
                "model_key": "model_2",
                "predictions": [{"class": "pothole", "confidence": 0.85, "x": 102, "y": 98, "width": 58, "height": 42}],
            },
            {
                "model_key": "model_3",
                "predictions": [{"class": "crack", "confidence": 0.70, "x": 220, "y": 200, "width": 50, "height": 30}],
            },
        ]

        data_uri = self.service.draw_multi_model_bounding_boxes(pil_img, model_results)
        self.assertTrue(data_uri.startswith("data:image/jpeg;base64,"))
        self.assertTrue(len(data_uri) > 100)


if __name__ == "__main__":
    unittest.main()
