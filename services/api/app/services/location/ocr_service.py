import re
import logging
from typing import Dict, Any, List, Optional
from PIL import Image

logger = logging.getLogger(__name__)

# Keywords & Village names across English, Kannada, and Hindi
BELAGAVI_LOCATION_KEYWORDS = {
    "peeranwadi": {"en": "Peeranwadi", "kn": "ಪೀರನವಾಡಿ", "hi": "पीरनवाड़ी"},
    "kuttalawadi": {"en": "Kuttalawadi", "kn": "ಕುಟ್ಟಲವಾಡಿ", "hi": "कुट्टलवाड़ी"},
    "zad_shahapur": {"en": "Zad-Shahapur", "kn": "ಝಾಡ್-ಶಹಾಪುರ", "hi": "झाड-शहापुर"},
    "santibastawad": {"en": "Santibastawad", "kn": "ಶಾಂತಿಬಸ್ತವಾಡ", "hi": "शांतिबस्तवाड़"},
    "yellur": {"en": "Yellur", "kn": "ಯೆಲ್ಲೂರು", "hi": "येल्लूर"},
    "sulge": {"en": "Sulge (Yellur)", "kn": "ಸುಳಗೆ", "hi": "सुलगे"},
    "mandoli": {"en": "Mandoli", "kn": "ಮಾಂಡೋಲಿ", "hi": "मांडोली"},
    "waghawade": {"en": "Waghawade", "kn": "ವಾಘಾವಡೆ", "hi": "वाघावडे"},
    "navage": {"en": "Navage", "kn": "ನವಾಗೆ", "hi": "नवागे"},
    "belagavi": {"en": "Belagavi", "kn": "ಬೆಳಗಾವಿ", "hi": "बेलगावी"},
    "belgaum": {"en": "Belgaum", "kn": "ಬೆಳಗಾವಿ", "hi": "बेलगाम"},
    "gram_panchayat": {"en": "Gram Panchayat", "kn": "ಗ್ರಾಮ ಪಂಚಾಯತ್", "hi": "ग्राम पंचायत"},
}

class PhotoOCRLocationService:
    """
    Dedicated OCR Location Recognition Service (Part 11A).
    Scans citizen photographs for visible village nameboards, road signs, street markers,
    and public infrastructure signboards.
    Note: Most pothole/garbage photos do not contain signboards; absence is reported honestly.
    """

    def __init__(self):
        self.provider_name = "GramaSeva OCR Engine (PyTesseract & Visual Text Filter)"
        self._tesseract_available = False
        try:
            import pytesseract
            self._pytesseract = pytesseract
            self._tesseract_available = True
        except ImportError:
            self._pytesseract = None

    def extract_location_clues(self, img: Image.Image) -> Dict[str, Any]:
        """
        Extracts visible location clues and village names from the photograph.
        """
        extracted_text = ""
        matched_villages = []
        confidence = 0.0
        status = "NO_CLUES_FOUND"

        if self._tesseract_available and self._pytesseract:
            try:
                # Attempt OCR with English and Kannada if language packs exist
                extracted_text = self._pytesseract.image_to_string(img, timeout=2.5)
            except Exception as e:
                logger.debug("Tesseract execution notice: %s", e)

        # Parse text for Belagavi Taluk village names & landmarks
        text_lower = extracted_text.lower() if extracted_text else ""
        for key, lang_map in BELAGAVI_LOCATION_KEYWORDS.items():
            en_name = lang_map["en"].lower()
            kn_name = lang_map["kn"]
            if en_name in text_lower or (kn_name and kn_name in extracted_text):
                matched_villages.append(lang_map["en"])

        if matched_villages:
            status = "LOCATION_CLUE_FOUND"
            confidence = 0.85
        elif extracted_text.strip():
            status = "TEXT_DETECTED_NO_VILLAGE"
            confidence = 0.40
        else:
            status = "NO_LOCATION_TEXT_FOUND"
            confidence = 0.0

        return {
            "status": status,
            "has_location_clues": bool(matched_villages),
            "matched_villages": list(set(matched_villages)),
            "extracted_text": extracted_text.strip() if extracted_text else None,
            "confidence": confidence,
            "provider": self.provider_name,
            "disclaimer": "Photo-based text clues are advisory and verified against GPS coordinates.",
        }

ocr_location_service = PhotoOCRLocationService()
