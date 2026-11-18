import os
import time
import hashlib
from io import BytesIO
from typing import Dict, Any, List, Optional, Union
from PIL import Image

_LOCAL_CFG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../Ultralytics"))
os.environ["YOLO_CONFIG_DIR"] = _LOCAL_CFG_DIR

EXPECTED_LEAK_SHA256 = "8670e5cef00b77e891cc48ce60c16c46b1d59e220c8f49a68db7f399680838ba"
MODEL_ID = "msunusi-pipeline-leak-yolo"
MODEL_VERSION = "1.0.0"

LEAK_CLASSES = {
    0: "crack",
    1: "gas",
    2: "leak",
    3: "no leak",
    4: "water",
}

LEAK_LIMITATIONS = [
    "Industrial pipeline visual detector; street scenes with rain runoff, puddles, or open gutters can introduce false positives.",
    "Camera bounding boxes cannot determine leak source, flow rate, pressure, or water potability.",
    "Detection output is advisory only. Gram Panchayat water works technician must confirm on site.",
]

class WaterLeakAdapter:
    def __init__(self, checkpoint_path: Optional[str] = None):
        self.checkpoint_path = checkpoint_path or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../models/pipeline_leak_detection.pt")
        )
        self.model = None
        self._is_loaded = False
        self._load_error = None
        self._checkpoint_hash = None

    def _verify_hash(self) -> bool:
        if not os.path.exists(self.checkpoint_path):
            self._load_error = f"Checkpoint file missing: {self.checkpoint_path}"
            return False
        hasher = hashlib.sha256()
        with open(self.checkpoint_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        self._checkpoint_hash = hasher.hexdigest()
        if self._checkpoint_hash != EXPECTED_LEAK_SHA256:
            self._load_error = f"Hash mismatch. Expected {EXPECTED_LEAK_SHA256}, got {self._checkpoint_hash}"
            return False
        return True

    def load_model(self) -> bool:
        if self._is_loaded and self.model is not None:
            return True
        if not self._verify_hash():
            return False
        try:
            from ultralytics import YOLO
            self.model = YOLO(self.checkpoint_path)
            self._is_loaded = True
            self._load_error = None
            return True
        except Exception as e:
            self._load_error = f"Failed to load leak model: {str(e)}"
            self._is_loaded = False
            return False

    def check_readiness(self) -> Dict[str, Any]:
        is_ready = self.load_model()
        return {
            "model_id": MODEL_ID,
            "version": MODEL_VERSION,
            "task": "water_leak_detection",
            "ready": is_ready,
            "checkpoint_sha256": self._checkpoint_hash or (EXPECTED_LEAK_SHA256 if os.path.exists(self.checkpoint_path) else None),
            "classes": list(LEAK_CLASSES.values()),
            "error": self._load_error,
        }

    def predict(
        self,
        image_input: Union[str, bytes, Image.Image],
        confidence_threshold: float = 0.25,
    ) -> Dict[str, Any]:
        start_time = time.perf_counter()
        if not self.load_model():
            latency_ms = round((time.perf_counter() - start_time) * 1000)
            return {
                "status": "unavailable",
                "task": "water_leak_detection",
                "category_suggestion": None,
                "confidence_score": None,
                "observations": [],
                "limitations": LEAK_LIMITATIONS,
                "requires_human_review": True,
                "model_id": MODEL_ID,
                "model_revision": self._checkpoint_hash or "unverified",
                "latency_ms": latency_ms,
                "error": self._load_error,
            }

        try:
            if isinstance(image_input, bytes):
                img = Image.open(BytesIO(image_input)).convert("RGB")
            elif isinstance(image_input, str):
                img = Image.open(image_input).convert("RGB")
            elif isinstance(image_input, Image.Image):
                img = image_input.convert("RGB")
            else:
                raise ValueError("Unsupported image input type")

            results = self.model.predict(img, conf=confidence_threshold, verbose=False)
            latency_ms = round((time.perf_counter() - start_time) * 1000)

            observations: List[Dict[str, Any]] = []
            top_confidence = 0.0

            if results and len(results) > 0:
                boxes = results[0].boxes
                if boxes is not None and len(boxes) > 0:
                    for box in boxes:
                        cls_id = int(box.cls[0].item())
                        conf = round(float(box.conf[0].item()), 3)
                        xyxy = [round(float(c), 1) for c in box.xyxy[0].tolist()]
                        label = LEAK_CLASSES.get(cls_id, f"Class {cls_id}")
                        if label != "no leak":
                            if conf > top_confidence:
                                top_confidence = conf
                            observations.append({
                                "class_id": cls_id,
                                "label": label,
                                "confidence": conf,
                                "bbox": xyxy,
                            })

            status = "completed" if len(observations) > 0 else "no_detections"
            category_suggestion = "water_leak" if any(o["label"] in ("leak", "water") for o in observations) else None

            return {
                "status": status,
                "task": "water_leak_detection",
                "category_suggestion": category_suggestion,
                "confidence_score": top_confidence if len(observations) > 0 else None,
                "observations": observations,
                "limitations": LEAK_LIMITATIONS,
                "requires_human_review": True,
                "model_id": MODEL_ID,
                "model_revision": self._checkpoint_hash or EXPECTED_LEAK_SHA256,
                "latency_ms": latency_ms,
                "prompt_message": (
                    "Possible visible water leak; source and flow are not confirmed. Please confirm."
                    if observations
                    else "No visible pipeline water leaks detected."
                ),
            }

        except Exception as e:
            latency_ms = round((time.perf_counter() - start_time) * 1000)
            return {
                "status": "failed",
                "task": "water_leak_detection",
                "category_suggestion": None,
                "confidence_score": None,
                "observations": [],
                "limitations": LEAK_LIMITATIONS,
                "requires_human_review": True,
                "model_id": MODEL_ID,
                "model_revision": self._checkpoint_hash or EXPECTED_LEAK_SHA256,
                "latency_ms": latency_ms,
                "error": str(e),
            }

water_leak_adapter = WaterLeakAdapter()
