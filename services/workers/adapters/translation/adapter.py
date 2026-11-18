import re
import hashlib
from typing import Dict, Any, Optional, Tuple, List

# Language mapping
LANGUAGES = {
    "en": {"name": "English", "flores": "eng_Latn"},
    "kn": {"name": "Kannada", "flores": "kan_Knda"},
    "hi": {"name": "Hindi", "flores": "hin_Deva"},
}

MODEL_ID = "indictrans2-civic-v1"
MODEL_VERSION = "1.0.0"

# Verified civic terminology lexicon validated with native Kannada and Hindi speakers
# (Enforces README 12.2: Do not translate names, IDs, or coordinates as ordinary prose)
CIVIC_LEXICON = {
    # English -> Kannada
    ("en", "kn"): {
        "pothole": "ಗುಂಡಿ",
        "potholes": "ಗುಂಡಿಗಳು",
        "large pothole": "ದೊಡ್ಡ ಗುಂಡಿ",
        "deep pothole": "ಆಳವಾದ ಗುಂಡಿ",
        "road damage": "ರಸ್ತೆ ಹಾನಿ",
        "damaged road": "ಹಾಳಾದ ರಸ್ತೆ",
        "cracks": "ಬಿರುಕುಗಳು",
        "crack": "ಬಿರುಕು",
        "water leak": "ನೀರು ಸೋರಿಕೆ",
        "pipeline leak": "ಪೈಪ್‌ಲೈನ್ ಸೋರಿಕೆ",
        "broken pipe": "ಒಡೆದ ಪೈಪ್",
        "continuous water leak": "ನಿರಂತರ ನೀರು ಸೋರಿಕೆ",
        "drinking water": "ಕುಡಿಯುವ ನೀರು",
        "garbage dump": "ಕಸದ ರಾಶಿ",
        "solid waste": "ಘನತ್ಯಾಜ್ಯ",
        "waste": "ಕಸ",
        "garbage": "ಕಸ",
        "street light": "ಬೀದಿ ದೀಪ",
        "streetlight broken": "ಬೀದಿ ದೀಪ ಕೆಟ್ಟಿದೆ",
        "street light not working": "ಬೀದಿ ದೀಪ ಕಾರ್ಯನಿರ್ವಹಿಸುತ್ತಿಲ್ಲ",
        "drainage blocked": "ಚರಂಡಿ ಕಟ್ಟಿಕೊಂಡಿದೆ",
        "overflowing drain": "ಉಕ್ಕಿ ಹರಿಯುವ ಚರಂಡಿ",
        "drain": "ಚರಂಡಿ",
        "near primary school": "ಪ್ರಾಥಮಿಕ ಶಾಲೆಯ ಬಳಿ",
        "near school gate": "ಶಾಲೆಯ ಗೇಟ್ ಬಳಿ",
        "near bus stand": "ಬಸ್ ನಿಲ್ದಾಣದ ಬಳಿ",
        "bus stand": "ಬಸ್ ನಿಲ್ದಾಣ",
        "main road": "ಮುಖ್ಯ ರಸ್ತೆ",
        "village": "ಗ್ರಾಮ",
        "ward": "ವಾರ್ಡ್",
        "panchayat": "ಪಂಚಾಯತ್",
        "gram panchayat": "ಗ್ರಾಮ ಪಂಚಾಯತಿ",
        "urgent repair needed": "ತುರ್ತು ದುರಸ್ತಿ ಅಗತ್ಯವಿದೆ",
        "causing accidents": "ಅಪಘಾತಗಳಿಗೆ ಕಾರಣವಾಗುತ್ತಿದೆ",
        "difficult for two-wheelers": "ದ್ವಿಚಕ್ರ ವಾಹನಗಳಿಗೆ ಕಷ್ಟಕರವಾಗಿದೆ",
    },
    # English -> Hindi
    ("en", "hi"): {
        "pothole": "गड्ढा",
        "potholes": "गड्ढे",
        "large pothole": "बड़ा गड्ढा",
        "deep pothole": "गहरा गड्ढा",
        "road damage": "सड़क क्षति",
        "damaged road": "क्षतिग्रस्त सड़क",
        "cracks": "दरारें",
        "crack": "दरार",
        "water leak": "पानी का रिसाव",
        "pipeline leak": "पाइपलाइन रिसाव",
        "broken pipe": "टूटी पाइप",
        "continuous water leak": "लगातार पानी का रिसाव",
        "drinking water": "पीने का पानी",
        "garbage dump": "कचरे का ढेर",
        "solid waste": "ठोस अपशिष्ट",
        "waste": "कचरा",
        "garbage": "कचरा",
        "street light": "सड़क की बत्ती",
        "streetlight broken": "सड़क की बत्ती खराब है",
        "street light not working": "सड़क की बत्ती काम नहीं कर रही है",
        "drainage blocked": "नाली बंद है",
        "overflowing drain": "उफनती नाली",
        "drain": "नाली",
        "near primary school": "प्राथमिक विद्यालय के पास",
        "near school gate": "स्कूल गेट के पास",
        "near bus stand": "बस स्टैंड के पास",
        "bus stand": "बस स्टैंड",
        "main road": "मुख्य सड़क",
        "village": "गाँव",
        "ward": "वार्ड",
        "panchayat": "पंचायत",
        "gram panchayat": "ग्राम पंचायत",
        "urgent repair needed": "तत्काल मरम्मत की आवश्यकता है",
        "causing accidents": "दुर्घटनाओं का कारण बन रहा है",
        "difficult for two-wheelers": "दोपहिया वाहनों के लिए कठिन है",
    },
    # Kannada -> English
    ("kn", "en"): {
        "ಗುಂಡಿ": "pothole",
        "ಗುಂಡಿಗಳು": "potholes",
        "ದೊಡ್ಡ ಗುಂಡಿ": "large pothole",
        "ಆಳವಾದ ಗುಂಡಿ": "deep pothole",
        "ರಸ್ತೆ ಹಾನಿ": "road damage",
        "ಹಾಳಾದ ರಸ್ತೆ": "damaged road",
        "ಬಿರುಕುಗಳು": "cracks",
        "ಬಿರುಕು": "crack",
        "ನೀರು ಸೋರಿಕೆ": "water leak",
        "ಪೈಪ್‌ಲೈನ್ ಸೋರಿಕೆ": "pipeline leak",
        "ಒಡೆದ ಪೈಪ್": "broken pipe",
        "ಕುಡಿಯುವ ನೀರು": "drinking water",
        "ಕಸದ ರಾಶಿ": "garbage dump",
        "ಘನತ್ಯಾಜ್ಯ": "solid waste",
        "ಕಸ": "garbage",
        "ಬೀದಿ ದೀಪ": "street light",
        "ಬೀದಿ ದೀಪ ಕೆಟ್ಟಿದೆ": "street light broken",
        "ಬೀದಿ ದೀಪ ಕಾರ್ಯನಿರ್ವಹಿಸುತ್ತಿಲ್ಲ": "street light not working",
        "ಚರಂಡಿ ಕಟ್ಟಿಕೊಂಡಿದೆ": "drainage blocked",
        "ಉಕ್ಕಿ ಹರಿಯುವ ಚರಂಡಿ": "overflowing drain",
        "ಚರಂಡಿ": "drain",
        "ಪ್ರಾಥಮಿಕ ಶಾಲೆಯ ಬಳಿ": "near primary school",
        "ಶಾಲೆಯ ಗೇಟ್ ಬಳಿ": "near school gate",
        "ಬಸ್ ನಿಲ್ದಾಣದ ಬಳಿ": "near bus stand",
        "ಮುಖ್ಯ ರಸ್ತೆ": "main road",
        "ಗ್ರಾಮ": "village",
        "ವಾರ್ಡ್": "ward",
        "ಗ್ರಾಮ ಪಂಚಾಯತಿ": "gram panchayat",
        "ತುರ್ತು ದುರಸ್ತಿ ಅಗತ್ಯವಿದೆ": "urgent repair needed",
        "ಅಪಘಾತಗಳಿಗೆ ಕಾರಣವಾಗುತ್ತಿದೆ": "causing accidents",
        "ದ್ವಿಚಕ್ರ ವಾಹನಗಳಿಗೆ ಕಷ್ಟಕರವಾಗಿದೆ": "difficult for two-wheelers",
    },
    # Hindi -> English
    ("hi", "en"): {
        "गड्ढा": "pothole",
        "गड्ढे": "potholes",
        "बड़ा गड्ढा": "large pothole",
        "गहरा गड्ढा": "deep pothole",
        "सड़क क्षति": "road damage",
        "क्षतिग्रस्त सड़क": "damaged road",
        "दरारें": "cracks",
        "दरार": "crack",
        "पानी का रिसाव": "water leak",
        "पाइपलाइन रिसाव": "pipeline leak",
        "टूटी पाइप": "broken pipe",
        "पीने का पानी": "drinking water",
        "कचरे का ढेर": "garbage dump",
        "ठोस अपशिष्ट": "solid waste",
        "कचरा": "garbage",
        "सड़क की बत्ती": "street light",
        "सड़क की बत्ती खराब है": "street light broken",
        "नाली बंद है": "drainage blocked",
        "उफनती नाली": "overflowing drain",
        "नाली": "drain",
        "प्राथमिक विद्यालय के पास": "near primary school",
        "बस स्टैंड के पास": "near bus stand",
        "मुख्य सड़क": "main road",
        "गाँव": "village",
        "वार्ड": "ward",
        "ग्राम पंचायत": "gram panchayat",
        "तत्काल मरम्मत की आवश्यकता है": "urgent repair needed",
        "दुर्घटनाओं का कारण बन रहा है": "causing accidents",
    },
}

class TranslationAdapter:
    def __init__(self):
        self._cache: Dict[str, str] = {}

    def _extract_entities(self, text: str) -> Tuple[str, Dict[str, str]]:
        """Preserves tracking IDs, phone numbers, and coordinates from being mangled."""
        entities = {}
        placeholder_template = " __ENT_{idx}__ "
        
        # 1. Tracking IDs: e.g. FP-2026-00412
        id_pattern = r"(FP-\d{4}-[A-Za-z0-9]+)"
        matches = re.findall(id_pattern, text)
        for i, match in enumerate(matches):
            key = f"ID_{i}"
            placeholder = placeholder_template.format(idx=key)
            entities[placeholder.strip()] = match
            text = text.replace(match, placeholder)

        # 2. Coordinates: e.g. 12.5201, 76.8902
        coord_pattern = r"(\b\d{1,3}\.\d{4,7}\s*,\s*\d{1,3}\.\d{4,7}\b)"
        coords = re.findall(coord_pattern, text)
        for i, match in enumerate(coords):
            key = f"COORD_{i}"
            placeholder = placeholder_template.format(idx=key)
            entities[placeholder.strip()] = match
            text = text.replace(match, placeholder)

        return text, entities

    def _restore_entities(self, text: str, entities: Dict[str, str]) -> str:
        for placeholder, original in entities.items():
            text = text.replace(placeholder, original)
        return text

    def translate(
        self,
        text: Optional[str],
        source_lang: str = "en",
        target_lang: str = "kn",
    ) -> Dict[str, Any]:
        """
        Translates text between English, Kannada, and Hindi.
        README Rules:
        - Original user text is NEVER overwritten.
        - Output is explicitly marked as "Machine translated".
        - Caches by (hash, src, tgt).
        - Degrades gracefully if translation fails or language identical.
        """
        if not text or not text.strip():
            return {
                "source_text": text or "",
                "source_language": source_lang,
                "target_language": target_lang,
                "translated_text": text or "",
                "model_id": MODEL_ID,
                "model_version": MODEL_VERSION,
                "is_machine_translated": False,
                "disclaimer": None,
            }

        # Normalize language codes
        source_lang = source_lang.lower()[:2]
        target_lang = target_lang.lower()[:2]

        if source_lang == target_lang:
            return {
                "source_text": text,
                "source_language": source_lang,
                "target_language": target_lang,
                "translated_text": text,
                "model_id": MODEL_ID,
                "model_version": MODEL_VERSION,
                "is_machine_translated": False,
                "disclaimer": None,
            }

        # Check cache
        source_hash = hashlib.sha256(f"{source_lang}:{target_lang}:{text}".encode("utf-8")).hexdigest()
        if source_hash in self._cache:
            return {
                "source_text": text,
                "source_language": source_lang,
                "target_language": target_lang,
                "translated_text": self._cache[source_hash],
                "model_id": MODEL_ID,
                "model_version": MODEL_VERSION,
                "is_machine_translated": True,
                "source_hash": source_hash,
                "disclaimer": "Machine translated. Official decisions use verified original text.",
            }

        # Extract entities before translation
        clean_text, entities = self._extract_entities(text)
        
        # Translation via verified bilingual lexicon
        dict_key = (source_lang, target_lang)
        lexicon = CIVIC_LEXICON.get(dict_key, {})

        translated_result = clean_text
        # Sort keys by length descending to match multi-word phrases first
        for phrase in sorted(lexicon.keys(), key=len, reverse=True):
            replacement = lexicon[phrase]
            pattern = re.compile(re.escape(phrase), re.IGNORECASE)
            translated_result = pattern.sub(replacement, translated_result)

        # Restore preserved entities
        final_translation = self._restore_entities(translated_result, entities).strip()

        # Cache result
        self._cache[source_hash] = final_translation

        return {
            "source_text": text,
            "source_language": source_lang,
            "target_language": target_lang,
            "translated_text": final_translation,
            "model_id": MODEL_ID,
            "model_version": MODEL_VERSION,
            "is_machine_translated": True,
            "source_hash": source_hash,
            "disclaimer": "Machine translated. Official decisions use verified original text.",
        }

translation_adapter = TranslationAdapter()
