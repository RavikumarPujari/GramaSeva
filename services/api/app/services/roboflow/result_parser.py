from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from app.services.roboflow.class_mapping import normalize_detected_class

@dataclass
class ParsedDetection:
    raw_class: str
    normalized_category: str
    confidence: float
    # Normalized relative coordinates (0.0 to 1.0)
    box_relative: List[float]  # [ymin, xmin, ymax, xmax]
    # Absolute pixel coordinates
    box_pixels: List[float]    # [xmin, ymin, xmax, ymax]
    center_x: float
    center_y: float
    width: float
    height: float
    model_source: str

@dataclass
class ModelInferenceResult:
    model_id: str
    model_key: str
    model_name: str
    specialist_type: str
    status: str  # "COMPLETED", "NO_DETECTIONS", "FAILED", "UNAUTHORIZED", "TIMEOUT"
    latency_ms: int
    image_width: int
    image_height: int
    detections: List[ParsedDetection]
    raw_predictions_count: int
    error: Optional[str] = None
    dominant_category: Optional[str] = None
    max_confidence: float = 0.0

class RoboflowResultParser:
    """
    Parses and standardizes real responses from Roboflow Object Detection models.
    Preserves confidence scores, normalizes classes, and converts coordinates.
    """

    @staticmethod
    def parse(
        response: Dict[str, Any],
        model_key: str,
        model_id: str,
        model_name: str,
        specialist_type: str,
        latency_ms: int,
        img_width: int = 640,
        img_height: int = 480,
        min_confidence: float = 0.20,
    ) -> ModelInferenceResult:
        predictions = response.get("predictions", [])
        resp_image = response.get("image", {})
        actual_w = resp_image.get("width") or img_width or 640
        actual_h = resp_image.get("height") or img_height or 480

        parsed_detections: List[ParsedDetection] = []
        category_counts: Dict[str, int] = {}
        category_confs: Dict[str, float] = {}

        for p in predictions:
            conf = float(p.get("confidence", 0.0))
            if conf < min_confidence:
                continue

            raw_label = str(p.get("class", p.get("label", "unknown")))
            normalized = normalize_detected_class(raw_label)

            # Roboflow coordinates are center x, center y, width, height in pixels
            cx = float(p.get("x", 0.0))
            cy = float(p.get("y", 0.0))
            w = float(p.get("width", 0.0))
            h = float(p.get("height", 0.0))

            xmin = max(0.0, cx - w / 2.0)
            ymin = max(0.0, cy - h / 2.0)
            xmax = min(float(actual_w), cx + w / 2.0)
            ymax = min(float(actual_h), cy + h / 2.0)

            # Relative coordinates [ymin, xmin, ymax, xmax] in 0.0 - 1.0 range
            rel_ymin = round(ymin / actual_h, 4) if actual_h > 0 else 0.0
            rel_xmin = round(xmin / actual_w, 4) if actual_w > 0 else 0.0
            rel_ymax = round(ymax / actual_h, 4) if actual_h > 0 else 1.0
            rel_xmax = round(xmax / actual_w, 4) if actual_w > 0 else 1.0

            detection = ParsedDetection(
                raw_class=raw_label,
                normalized_category=normalized,
                confidence=round(conf, 4),
                box_relative=[rel_ymin, rel_xmin, rel_ymax, rel_xmax],
                box_pixels=[round(xmin, 1), round(ymin, 1), round(xmax, 1), round(ymax, 1)],
                center_x=round(cx, 1),
                center_y=round(cy, 1),
                width=round(w, 1),
                height=round(h, 1),
                model_source=model_key,
            )
            parsed_detections.append(detection)

            category_counts[normalized] = category_counts.get(normalized, 0) + 1
            category_confs[normalized] = max(category_confs.get(normalized, 0.0), conf)

        # Sort detections by confidence descending
        parsed_detections.sort(key=lambda d: d.confidence, reverse=True)

        dominant_cat = None
        max_conf = 0.0
        if category_confs:
            dominant_cat = max(category_confs.items(), key=lambda item: item[1])[0]
            max_conf = category_confs[dominant_cat]

        status = "COMPLETED" if parsed_detections else "NO_DETECTIONS"

        return ModelInferenceResult(
            model_id=model_id,
            model_key=model_key,
            model_name=model_name,
            specialist_type=specialist_type,
            status=status,
            latency_ms=latency_ms,
            image_width=actual_w,
            image_height=actual_h,
            detections=parsed_detections,
            raw_predictions_count=len(predictions),
            dominant_category=dominant_cat,
            max_confidence=round(max_conf, 4),
        )
