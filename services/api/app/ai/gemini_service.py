import os
import json
import base64
import re
import urllib.request
import urllib.error
from typing import Optional, Dict, Any, List
from PIL import Image
import io
from app.core.config import settings

class GeminiService:
    """
    Google Gemini Vision & Language Intelligence Service for GramaSeva (Part 4).
    Strictly follows project governance:
    - Never replaces specialized YOLO computer vision models.
    - Operates strictly on the backend with zero frontend exposure of API keys.
    - Multimodal understanding, complaint generation, PDO summarization, OCR assistance,
      before/after verification, and multilingual translation.
    - Gracefully falls back to deterministic local heuristics when offline, unconfigured, or throttled.
    """

    PILOT_VILLAGES = [
        "Peeranwadi", "Kuttalawadi", "Zad-Shahapur", "Santibastawad",
        "Yellur", "Sulge (Yellur)", "Mandoli", "Waghawade", "Navage"
    ]

    def __init__(self):
        self.api_key = settings.gemini_api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
        self.model_name = settings.gemini_model or os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        self.timeout_seconds = 8.0

    def is_available(self) -> bool:
        """Checks if a valid, non-placeholder Gemini API key is configured."""
        if not self.api_key or len(self.api_key.strip()) < 15:
            return False
        placeholder_tokens = ["your_", "todo", "xxx", "placeholder"]
        return not any(p in self.api_key.lower() for p in placeholder_tokens)

    def _call_gemini_rest(self, contents: list, generation_config: Optional[dict] = None) -> Optional[dict]:
        """Executes REST request to Generative Language API without third-party SDK dependencies."""
        if not self.is_available():
            return None

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
        body = {"contents": contents}
        if generation_config:
            body["generationConfig"] = generation_config

        try:
            payload = json.dumps(body).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                if response.status == 200:
                    return json.loads(response.read().decode("utf-8"))
        except Exception as e:
            # Silent fallback to deterministic heuristics
            return None
        return None

    # 1. Multimodal Image Understanding
    def analyze_image(self, image_bytes: bytes, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Multimodal visual analysis of a civic problem photograph.
        Returns structured validation, category, severity, and visual observations.
        """
        category_hint = (context or {}).get("category_hint", "")
        village_name = (context or {}).get("village_name", "Belagavi Taluk")

        if self.is_available():
            b64_img = base64.b64encode(image_bytes).decode("utf-8")
            prompt = (
                "You are an expert civil inspector for Karnataka Gram Panchayats. "
                "Analyze this civic complaint photograph and reply ONLY with a valid JSON object matching this schema:\n"
                "{\n"
                '  "is_civic_issue": true/false,\n'
                '  "primary_category": "ROADS" | "GARBAGE" | "WATER" | "DRAINAGE" | "STREETLIGHT" | "OTHER",\n'
                '  "severity_assessment": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",\n'
                '  "visual_summary": "factual 1-sentence visual description",\n'
                '  "detected_elements": ["item1", "item2"],\n'
                '  "civic_validity_explanation": "why this requires GP intervention",\n'
                '  "suggested_action": "recommended municipal action",\n'
                '  "confidence": 0.0 to 1.0\n'
                "}\n"
                f"Context hint: {category_hint}. Location: {village_name}."
            )
            contents = [{
                "parts": [
                    {"inline_data": {"mime_type": "image/jpeg", "data": b64_img}},
                    {"text": prompt}
                ]
            }]
            result = self._call_gemini_rest(contents, {"temperature": 0.1, "maxOutputTokens": 300})
            if result and "candidates" in result and result["candidates"]:
                raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                # Clean code fences if present
                clean_json = re.sub(r"^```json\s*", "", raw_text)
                clean_json = re.sub(r"\s*```$", "", clean_json)
                try:
                    parsed = json.loads(clean_json)
                    parsed["source"] = "gemini-multimodal"
                    return parsed
                except Exception:
                    pass

        # Deterministic Heuristic Fallback
        cat = category_hint if category_hint in ["ROADS", "GARBAGE", "WATER", "DRAINAGE", "STREETLIGHT"] else "ROADS"
        return {
            "is_civic_issue": True,
            "primary_category": cat,
            "severity_assessment": "MEDIUM",
            "visual_summary": f"Civic defect observed requiring inspection at {village_name}.",
            "detected_elements": ["infrastructure damage", "public path issue"],
            "civic_validity_explanation": "Defect is located in a public right-of-way within Gram Panchayat jurisdiction.",
            "suggested_action": "Deploy field maintenance crew for on-site assessment and repair.",
            "confidence": 0.85,
            "source": "deterministic-heuristic"
        }

    # 2. Complaint Description & Title Generation
    def generate_complaint_details(
        self,
        category: str,
        defect_label: Optional[str] = None,
        village_name: Optional[str] = None,
        citizen_notes: Optional[str] = None,
        locale: str = "en"
    ) -> Dict[str, str]:
        """
        Generates a clear, professional title and description while strictly
        preserving citizen-provided notes and context.
        """
        v_name = village_name or "Belagavi Taluk"
        defect = defect_label or "Infrastructure Defect"

        if self.is_available():
            prompt = (
                f"You are a public works documentation assistant for Karnataka Gram Panchayats. "
                f"Create a concise title and a formal report description in {locale} for a civic issue.\n"
                f"Category: {category}\n"
                f"Detected defect: {defect}\n"
                f"Village: {v_name}\n"
                f"Citizen notes: {citizen_notes or 'None provided'}\n\n"
                f"Return ONLY a JSON object: {{\"title\": \"...\", \"description\": \"...\"}}."
            )
            result = self._call_gemini_rest([{"parts": [{"text": prompt}]}], {"temperature": 0.2, "maxOutputTokens": 200})
            if result and "candidates" in result and result["candidates"]:
                raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                clean_json = re.sub(r"^```json\s*", "", raw_text)
                clean_json = re.sub(r"\s*```$", "", clean_json)
                try:
                    data = json.loads(clean_json)
                    if "title" in data and "description" in data:
                        return data
                except Exception:
                    pass

        # Deterministic Fallback supporting English, Kannada and Hindi
        cat_formatted = category.replace("_", " ").title()
        loc_clean = (locale or "en").lower()

        if loc_clean in ["kn", "kannada"]:
            title = f"{v_name} ನಲ್ಲಿ {defect} ಸಮಸ್ಯೆ"
            desc = (
                f"{v_name}, ಬೆಳಗಾವಿ ತಾಲೂಕಿನಲ್ಲಿ {cat_formatted} ({defect}) ಸಮಸ್ಯೆ ಕಂಡುಬಂದಿದೆ. "
                f"ಗ್ರಾಮ ಪಂಚಾಯತಿ ಅಧಿಕಾರಿಗಳು ತಕ್ಷಣ ಸ್ಥಳ ಪರಿಶೀಲನೆ ನಡೆಸಿ ದುರಸ್ತಿ ಕೈಗೊಳ್ಳಬೇಕಾಗಿ ಕೋರಲಾಗಿದೆ."
            )
        elif loc_clean in ["hi", "hindi"]:
            title = f"{v_name} में {defect} की समस्या"
            desc = (
                f"{v_name}, बेलगावी तालुक में {cat_formatted} ({defect}) की नागरिक समस्या की सूचना मिली है। "
                f"ग्राम पंचायत अधिकारियों से स्थल निरीक्षण एवं शीघ्र मरम्मत का अनुरोध किया जाता है।"
            )
        else:
            title = f"{defect.title()} reported in {v_name}"
            desc = (
                f"A {cat_formatted.lower()} issue ({defect}) has been reported at {v_name}, Belagavi Taluk. "
                f"Public works inspection and necessary maintenance are requested."
            )

        if citizen_notes:
            desc += f" Citizen notes: \"{citizen_notes.strip()}\"."
        return {"title": title, "description": desc}

    # 3. Summarization for PDO Dashboards
    def summarize_for_pdo(self, issue_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Produces an executive summary for Panchayat Development Officers (PDO),
        categorizing urgency, scope of work, and public health/safety risks.
        """
        category = issue_data.get("category", "General Civic")
        village = issue_data.get("village_name", "Belagavi Taluk")
        severity = issue_data.get("severity", "MEDIUM")
        notes = issue_data.get("description", "")

        if self.is_available():
            prompt = (
                f"You are a municipal technical officer for Belagavi District. "
                f"Summarize this issue for the Panchayat Development Officer (PDO):\n"
                f"Category: {category}, Village: {village}, Severity: {severity}, Details: {notes}\n\n"
                f"Return ONLY valid JSON matching:\n"
                f"{{\n"
                f'  "executive_summary": "1-2 sentence briefing for PDO",\n'
                f'  "urgency_level": "ROUTINE" | "URGENT" | "EMERGENCY",\n'
                f'  "recommended_department": "Engineering / Sanitation / Water Supply",\n'
                f'  "estimated_scope_of_work": "brief repair scope",\n'
                f'  "key_risks": ["risk1", "risk2"]\n'
                f"}}"
            )
            result = self._call_gemini_rest([{"parts": [{"text": prompt}]}], {"temperature": 0.2, "maxOutputTokens": 250})
            if result and "candidates" in result and result["candidates"]:
                raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                clean_json = re.sub(r"^```json\s*", "", raw_text)
                clean_json = re.sub(r"\s*```$", "", clean_json)
                try:
                    return json.loads(clean_json)
                except Exception:
                    pass

        # Deterministic Fallback
        dept_map = {
            "road_damage": "Panchayat Engineering Section (Roads)",
            "water_leak": "Rural Water Supply & Sanitation (RWSS)",
            "garbage": "Grama Panchayat Sanitation Team",
            "street_light": "Rural Electrification Unit",
        }
        urgency = "URGENT" if severity in ["HIGH", "CRITICAL"] else "ROUTINE"
        return {
            "executive_summary": f"Reported {category.replace('_', ' ')} at {village} requiring verification and action.",
            "urgency_level": urgency,
            "recommended_department": dept_map.get(category, "Gram Panchayat Public Works"),
            "estimated_scope_of_work": "Physical verification, material requisition, and localized corrective maintenance.",
            "key_risks": ["Public inconvenience", "Pedestrian or vehicle transit disruption"]
        }

    # 4. OCR & Photo Location Clues
    def extract_location_clues(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Extracts visible text, village names, and landmark signboards from the photograph.
        Never fabricates coordinates.
        """
        if self.is_available():
            b64_img = base64.b64encode(image_bytes).decode("utf-8")
            prompt = (
                "Inspect this photo for any legible Kannada or English signboards, village names, "
                "Gram Panchayat office boards, mile markers, or landmark signs in Belagavi District.\n"
                "Return ONLY a JSON object:\n"
                "{\n"
                '  "detected_text": ["text1", "text2"],\n'
                '  "possible_village_names": ["Village1"],\n'
                '  "visible_landmarks": ["Temple", "School"],\n'
                '  "signboard_type": "GP_OFFICE" | "DIRECTION_BOARD" | "SHOP" | null,\n'
                '  "confidence": 0.0 to 1.0\n'
                "}"
            )
            contents = [{
                "parts": [
                    {"inline_data": {"mime_type": "image/jpeg", "data": b64_img}},
                    {"text": prompt}
                ]
            }]
            result = self._call_gemini_rest(contents, {"temperature": 0.1, "maxOutputTokens": 200})
            if result and "candidates" in result and result["candidates"]:
                raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                clean_json = re.sub(r"^```json\s*", "", raw_text)
                clean_json = re.sub(r"\s*```$", "", clean_json)
                try:
                    return json.loads(clean_json)
                except Exception:
                    pass

        # Deterministic Fallback
        return {
            "detected_text": [],
            "possible_village_names": [],
            "visible_landmarks": [],
            "signboard_type": None,
            "confidence": 0.0
        }

    # 5. Before & After Evidence Comparison
    def compare_before_after(
        self,
        before_image_bytes: bytes,
        after_image_bytes: bytes,
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Advisory comparison between citizen's initial complaint photo and worker's repair photo.
        PDO approval remains strictly mandatory.
        """
        if self.is_available():
            b64_before = base64.b64encode(before_image_bytes).decode("utf-8")
            b64_after = base64.b64encode(after_image_bytes).decode("utf-8")
            prompt = (
                "Compare these two civic photos (Image 1 = Before repair, Image 2 = After repair). "
                "Assess if the civic defect shown in Image 1 appears repaired or mitigated in Image 2. "
                "Check for scene consistency and mismatch.\n"
                "Return ONLY a JSON object:\n"
                "{\n"
                '  "visible_change": true/false,\n'
                '  "possible_mismatch": true/false,\n'
                '  "insufficient_evidence": true/false,\n'
                '  "visual_consistency_score": 0.0 to 1.0,\n'
                '  "difference_summary": "1-2 sentence description of differences",\n'
                '  "suggested_advisory_decision": "RECOMMEND_APPROVAL" | "NEEDS_INSPECTION" | "REJECT_INSUFFICIENT_EVIDENCE",\n'
                '  "advisory_notes": "Advisory note for Panchayat Development Officer"\n'
                "}"
            )
            contents = [{
                "parts": [
                    {"text": "Before repair photograph:"},
                    {"inline_data": {"mime_type": "image/jpeg", "data": b64_before}},
                    {"text": "After repair photograph:"},
                    {"inline_data": {"mime_type": "image/jpeg", "data": b64_after}},
                    {"text": prompt}
                ]
            }]
            result = self._call_gemini_rest(contents, {"temperature": 0.1, "maxOutputTokens": 300})
            if result and "candidates" in result and result["candidates"]:
                raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                clean_json = re.sub(r"^```json\s*", "", raw_text)
                clean_json = re.sub(r"\s*```$", "", clean_json)
                try:
                    data = json.loads(clean_json)
                    data["status"] = "COMPLETED"
                    return data
                except Exception:
                    pass

        # Deterministic Heuristic Comparison (Perceptual similarity fallback)
        try:
            img1 = Image.open(io.BytesIO(before_image_bytes)).convert("L").resize((32, 32))
            img2 = Image.open(io.BytesIO(after_image_bytes)).convert("L").resize((32, 32))
            b1 = img1.tobytes()
            b2 = img2.tobytes()
            diff_sum = sum(abs(p1 - p2) for p1, p2 in zip(b1, b2))
            max_diff = 255 * 1024
            similarity = max(0.0, min(1.0, 1.0 - (diff_sum / max_diff)))
            visible_change = similarity < 0.95 and similarity > 0.40
            mismatch = similarity <= 0.40
        except Exception:
            similarity = 0.75
            visible_change = True
            mismatch = False

        return {
            "visible_change": visible_change,
            "possible_mismatch": mismatch,
            "insufficient_evidence": False,
            "visual_consistency_score": round(similarity, 3),
            "difference_summary": "Visual differences detected between before-repair and after-repair evidence.",
            "suggested_advisory_decision": "RECOMMEND_APPROVAL" if visible_change and not mismatch else "NEEDS_INSPECTION",
            "advisory_notes": "Automated advisory verification only. Final clearance requires PDO inspection.",
            "status": "COMPLETED"
        }

    # 6. Multilingual Translation
    def translate_text(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        Translates text between Kannada (kn), English (en), and Hindi (hi).
        Strictly preserves tracking IDs (GS-2026-XXXX, SUB-XXXX), URLs, and numbers.
        """
        if not text or source_lang == target_lang:
            return text

        if self.is_available():
            prompt = (
                f"Translate the following civic complaint text from {source_lang} to {target_lang}. "
                f"STRICT INSTRUCTION: Do NOT alter tracking IDs (e.g., GS-2026-XXXX, SUB-XXXX), "
                f"reference codes, numbers, URLs, or telephone numbers.\n\n"
                f"Text:\n{text}"
            )
            result = self._call_gemini_rest([{"parts": [{"text": prompt}]}], {"temperature": 0.1, "maxOutputTokens": 300})
            if result and "candidates" in result and result["candidates"]:
                return result["candidates"][0]["content"]["parts"][0]["text"].strip()

        # Deterministic Fallback
        return text

    # Backward compatibility with existing router calls
    def generate_civic_description(
        self,
        category: str,
        defect_label: Optional[str],
        village_name: str,
        locale: str = "en"
    ) -> Optional[str]:
        details = self.generate_complaint_details(
            category=category,
            defect_label=defect_label,
            village_name=village_name,
            locale=locale
        )
        return details.get("description")

gemini_service = GeminiService()
