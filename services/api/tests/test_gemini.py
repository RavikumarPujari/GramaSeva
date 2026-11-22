import os
import sys
import io
import unittest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from PIL import Image
from app.ai.gemini_service import gemini_service, GeminiService

class TestGeminiService(unittest.TestCase):
    def setUp(self):
        self.service = gemini_service
        # Generate a small in-memory test image
        img = Image.new("RGB", (100, 100), color=(180, 100, 50))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        self.test_image_bytes = buf.getvalue()

    def test_01_gemini_config_and_availability(self):
        """Verifies Gemini service configuration and availability check."""
        self.assertIsNotNone(self.service.model_name)
        self.assertIn("gemini", self.service.model_name.lower())
        # Placeholder keys should be safely recognized as unavailable
        temp_service = GeminiService()
        temp_service.api_key = "your_gemini_api_key_here"
        self.assertFalse(temp_service.is_available())

    def test_02_multimodal_image_understanding(self):
        """Verifies multimodal image analysis returns strict civic schema."""
        res = self.service.analyze_image(
            self.test_image_bytes,
            context={"category_hint": "ROADS", "village_name": "Peeranwadi"}
        )
        self.assertIsInstance(res, dict)
        self.assertIn("is_civic_issue", res)
        self.assertIn("primary_category", res)
        self.assertIn("severity_assessment", res)
        self.assertIn("visual_summary", res)
        self.assertIn("detected_elements", res)
        self.assertIn("suggested_action", res)
        self.assertIn("confidence", res)
        self.assertTrue(res["is_civic_issue"])
        self.assertGreaterEqual(res["confidence"], 0.0)

    def test_03_complaint_description_and_title_generation(self):
        """Verifies complaint generation preserves citizen dialect and notes."""
        citizen_notes = "Deep crater near bus stop since Monday morning."
        res = self.service.generate_complaint_details(
            category="road_damage",
            defect_label="Pothole",
            village_name="Yellur",
            citizen_notes=citizen_notes,
        )
        self.assertIn("title", res)
        self.assertIn("description", res)
        self.assertTrue(len(res["title"]) > 5)
        # Citizen notes must be preserved
        self.assertIn("crater near bus stop", res["description"].lower())

    def test_04_pdo_summarization(self):
        """Verifies executive summary production for Panchayat Development Officers."""
        issue_data = {
            "category": "road_damage",
            "village_name": "Mandoli",
            "severity": "HIGH",
            "description": "Large road breach causing vehicle slowdown."
        }
        res = self.service.summarize_for_pdo(issue_data)
        self.assertIn("executive_summary", res)
        self.assertIn("urgency_level", res)
        self.assertIn("recommended_department", res)
        self.assertIn("estimated_scope_of_work", res)
        self.assertIn("key_risks", res)
        self.assertEqual(res["urgency_level"], "URGENT")
        self.assertIsInstance(res["key_risks"], list)

    def test_05_extract_location_clues(self):
        """Verifies location clues extraction returns valid schema without fabricating coordinates."""
        res = self.service.extract_location_clues(self.test_image_bytes)
        self.assertIn("detected_text", res)
        self.assertIn("possible_village_names", res)
        self.assertIn("visible_landmarks", res)
        self.assertIn("confidence", res)
        # Coordinates must never be fabricated in this method
        self.assertNotIn("latitude", res)
        self.assertNotIn("longitude", res)

    def test_06_before_after_comparison(self):
        """Verifies before/after advisory comparison between complaint and repair evidence."""
        img2 = Image.new("RGB", (100, 100), color=(100, 180, 50))
        buf2 = io.BytesIO()
        img2.save(buf2, format="JPEG")
        after_bytes = buf2.getvalue()

        res = self.service.compare_before_after(self.test_image_bytes, after_bytes, category="road_damage")
        self.assertIn("visible_change", res)
        self.assertIn("possible_mismatch", res)
        self.assertIn("visual_consistency_score", res)
        self.assertIn("suggested_advisory_decision", res)
        self.assertIn("advisory_notes", res)
        self.assertGreaterEqual(res["visual_consistency_score"], 0.0)
        self.assertLessEqual(res["visual_consistency_score"], 1.0)

    def test_07_multilingual_translation_preserves_identifiers(self):
        """Verifies translation preserves tracking IDs and numeric tokens intact."""
        raw_text = "Complaint GS-2026-BEL-0042 at Peeranwadi requires Rs. 5000 repair."
        trans = self.service.translate_text(raw_text, source_lang="en", target_lang="kn")
        self.assertIn("GS-2026-BEL-0042", trans)
        self.assertIn("5000", trans)

if __name__ == "__main__":
    unittest.main()
