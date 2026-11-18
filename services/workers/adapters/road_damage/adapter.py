import os
import time
import hashlib
from io import BytesIO
from typing import Dict, Any, List, Optional, Union
from PIL import Image

# Ensure local configuration directory for Ultralytics in workspace
_LOCAL_CFG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../Ultralytics"))
os.environ["YOLO_CONFIG_DIR"] = _LOCAL_CFG_DIR

EXPECTED_SHA256 = "7f2ceb8f6f3dfcc8fffd98cb488281be725150aed0f06cf21c4db72b5cd0a62b"
MODEL_ID = "oracl4-rdd-yolov8s"
MODEL_VERSION = "1.0.0"

CLASS_MAPPING = {
    0: "Longitudinal Crack",
    1: "Transverse Crack",
    2: "Alligator Crack",
    3: "Potholes",
}

ROAD_DAMAGE_LIMITATIONS = [
    "Image analysis does not measure pothole depth, water depth, or subsurface structural failure.",
    "Road debris, mud, shadows, and water reflection can affect visual confidence.",
    "Detection output is advisory only. A human reviewer or citizen must confirm the condition.",
]

class RoadDamageAdapter:
    def __init__(self, checkpoint_path: Optional[str] = None):
        self.checkpoint_path = checkpoint_path or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../models/YOLOv8_Small_RDD.pt")
        )
        self.model = None
        self._is_loaded = False
        self._load_error = None
        self._checkpoint_hash = None

    def _verify_checkpoint_hash(self) -> bool:
        if not os.path.exists(self.checkpoint_path):
            self._load_error = f"Checkpoint file missing: {self.checkpoint_path}"
            return False
        
        hasher = hashlib.sha256()
        with open(self.checkpoint_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        self._checkpoint_hash = hasher.hexdigest()
        
        if self._checkpoint_hash != EXPECTED_SHA256:
            self._load_error = (
                f"Checkpoint hash mismatch. Expected {EXPECTED_SHA256}, got {self._checkpoint_hash}"
            )
            return False
        return True

    def load_model(self) -> bool:
        if self._is_loaded and self.model is not None:
            return True

        if not self._verify_checkpoint_hash():
            return False

        try:
            from ultralytics import YOLO
            self.model = YOLO(self.checkpoint_path)
            self._is_loaded = True
            self._load_error = None
            return True
        except Exception as e:
            self._load_error = f"Failed to load YOLO model: {str(e)}"
            self._is_loaded = False
            return False

    def check_readiness(self) -> Dict[str, Any]:
        """Returns readiness and provenance metrics for the road damage model."""
        is_ready = self.load_model()
        return {
            "model_id": MODEL_ID,
            "version": MODEL_VERSION,
            "task": "road_damage_detection",
            "ready": is_ready,
            "checkpoint_path": self.checkpoint_path,
            "checkpoint_sha256": self._checkpoint_hash or (EXPECTED_SHA256 if os.path.exists(self.checkpoint_path) else None),
            "classes": list(CLASS_MAPPING.values()),
            "error": self._load_error,
        }

    def predict(
        self,
        image_input: Union[str, bytes, Image.Image],
        confidence_threshold: float = 0.25,
    ) -> Dict[str, Any]:
        """
        Executes real forward inference on an image and returns structured predictions.
        Falls back safely if model is unavailable.
        """
        start_time = time.perf_counter()

        # Check model availability
        if not self.load_model():
            latency_ms = round((time.perf_counter() - start_time) * 1000)
            return {
                "status": "unavailable",
                "task": "road_damage_detection",
                "category_suggestion": None,
                "confidence_score": None,
                "observations": [],
                "limitations": [
                    "Model checkpoint unavailable or failed readiness verification.",
                    "Full manual review required. Zero automated predictions.",
                ],
                "requires_human_review": True,
                "model_id": MODEL_ID,
                "model_revision": self._checkpoint_hash or "unverified",
                "latency_ms": latency_ms,
                "error": self._load_error,
            }

        try:
            # Prepare image
            if isinstance(image_input, bytes):
                img = Image.open(BytesIO(image_input)).convert("RGB")
            elif isinstance(image_input, str):
                if not os.path.exists(image_input):
                    raise FileNotFoundError(f"Image file not found: {image_input}")
                img = Image.open(image_input).convert("RGB")
            elif isinstance(image_input, Image.Image):
                img = image_input.convert("RGB")
            else:
                raise ValueError("Unsupported image input type")

            # Real YOLOv8 inference
            results = self.model.predict(img, conf=confidence_threshold, verbose=False)
            latency_ms = round((time.perf_counter() - start_time) * 1000)

            observations: List[Dict[str, Any]] = []
            top_confidence = 0.0

            if results and len(results) > 0:
                first_res = results[0]
                boxes = first_res.boxes
                if boxes is not None and len(boxes) > 0:
                    for box in boxes:
                        cls_id = int(box.cls[0].item())
                        conf = round(float(box.conf[0].item()), 3)
                        xyxy = [round(float(c), 1) for c in box.xyxy[0].tolist()]

                        label = CLASS_MAPPING.get(cls_id, f"Road Defect {cls_id}")
                        if conf > top_confidence:
                            top_confidence = conf

                        observations.append({
                            "class_id": cls_id,
                            "label": label,
                            "confidence": conf,
                            "bbox": xyxy,  # [x1, y1, x2, y2]
                        })

            status = "completed" if len(observations) > 0 else "no_detections"
            category_suggestion = "road_damage" if len(observations) > 0 else None

            return {
                "status": status,
                "task": "road_damage_detection",
                "category_suggestion": category_suggestion,
                "confidence_score": top_confidence if len(observations) > 0 else None,
                "observations": observations,
                "limitations": ROAD_DAMAGE_LIMITATIONS,
                "requires_human_review": True,  # Always advisory per FixProof rules
                "model_id": MODEL_ID,
                "model_revision": self._checkpoint_hash or EXPECTED_SHA256,
                "latency_ms": latency_ms,
                "prompt_message": (
                    f"Possible road damage detected: {', '.join(set(o['label'] for o in observations))}. Please confirm."
                    if observations
                    else "No road damage patterns detected. Manual triage required."
                ),
            }

        except Exception as e:
            latency_ms = round((time.perf_counter() - start_time) * 1000)
            return {
                "status": "failed",
                "task": "road_damage_detection",
                "category_suggestion": None,
                "confidence_score": None,
                "observations": [],
                "limitations": ROAD_DAMAGE_LIMITATIONS,
                "requires_human_review": True,
                "model_id": MODEL_ID,
                "model_revision": self._checkpoint_hash or EXPECTED_SHA256,
                "latency_ms": latency_ms,
                "error": str(e),
            }

road_damage_adapter = RoadDamageAdapter()
