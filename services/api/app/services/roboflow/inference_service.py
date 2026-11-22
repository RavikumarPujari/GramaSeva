import os
import io
import time
import base64
import logging
import tempfile
from typing import List, Optional, Dict, Any, Tuple
from PIL import Image, ImageDraw, ImageFont

from app.services.roboflow.client import RoboflowClientManager
from app.services.roboflow.model_registry import model_registry, ModelDescriptor
from app.services.roboflow.result_parser import RoboflowResultParser, ModelInferenceResult, ParsedDetection
from app.services.roboflow.prediction_comparator import RoboflowPredictionComparator, AggregatedComparison
from app.services.roboflow.validation import validate_image_bytes, check_image_lighting_and_quality

logger = logging.getLogger(__name__)

# Bounding box color palette by normalized civic category
CATEGORY_COLORS = {
    "garbage": "#E11D48",        # Rose / Bright Red
    "road_damage": "#D97706",    # Amber / Orange
    "drainage": "#0284C7",       # Sky Blue
    "water_leak": "#2563EB",     # Royal Blue
    "streetlight": "#7C3AED",    # Purple
    "public_facility": "#059669", # Emerald Green
    "other": "#64748B",          # Slate Gray
}

class RoboflowCentralEngine:
    """
    Central 5-Model Roboflow Recognition & Specialist Routing Engine:
      1. garbage_detection-wvzwv-n8vsv/1 (Garbage Specialist)
      2. road-damage-detection-fn0qh/1 (Road Damage Specialist)
      3. water-logging-a7zhi/1 (Waterlogging Specialist)
      4. civic-issues-lroee/3 (Civic Infrastructure 1)
      5. civic-issues-nq7sy-bh8t3/1 (Civic Infrastructure 2)
    """

    def __init__(self):
        self.registry = model_registry
        self.client_manager = RoboflowClientManager

    def route_models(
        self,
        category_hint: Optional[str] = None,
        full_evaluation: bool = False,
    ) -> List[ModelDescriptor]:
        """
        Intelligently routes models based on category hint or full-evaluation mode (Part 5).
        """
        all_models = self.registry.get_all_models()

        if full_evaluation:
            return all_models

        clean_hint = (category_hint or "").strip().lower()

        if clean_hint in ("garbage", "waste", "litter", "solid_waste"):
            # Run garbage specialist + both civic validators
            keys = ["garbage", "civic_1", "civic_2"]
        elif clean_hint in ("road_damage", "pothole", "cracks", "potholes"):
            # Run road damage specialist + both civic validators
            keys = ["road", "civic_1", "civic_2"]
        elif clean_hint in ("drainage", "waterlogging", "standing_water", "water_leak", "leak"):
            # Run waterlogging specialist + both civic validators
            keys = ["waterlogging", "civic_1", "civic_2"]
        else:
            # Default balanced evaluation: Road + Garbage + Civic 1
            keys = ["road", "garbage", "civic_1"]

        selected = [self.registry.get_model(k) for k in keys if self.registry.get_model(k)]
        return selected

    def infer_single_model(
        self,
        descriptor: ModelDescriptor,
        temp_img_path: str,
        img_width: int,
        img_height: int,
    ) -> ModelInferenceResult:
        """
        Executes inference for a single model with timing and complete failure isolation.
        """
        start_time = time.time()
        client = self.client_manager.get_client()

        if not client or not self.client_manager.is_configured():
            latency_ms = int((time.time() - start_time) * 1000)
            self.registry.update_model_health(
                descriptor.key,
                status="UNAUTHORIZED",
                latency_ms=latency_ms,
                error="Roboflow API key not configured or using placeholder.",
            )
            return ModelInferenceResult(
                model_id=descriptor.model_id,
                model_key=descriptor.key,
                model_name=descriptor.name,
                specialist_type=descriptor.specialist_type,
                status="UNAUTHORIZED",
                latency_ms=latency_ms,
                image_width=img_width,
                image_height=img_height,
                detections=[],
                raw_predictions_count=0,
                error="Roboflow API key not configured.",
            )

        try:
            import socket
            orig_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(2.5)
            try:
                raw_res = client.infer(temp_img_path, model_id=descriptor.model_id)
            finally:
                socket.setdefaulttimeout(orig_timeout)

            latency_ms = int((time.time() - start_time) * 1000)

            parsed = RoboflowResultParser.parse(
                response=raw_res,
                model_key=descriptor.key,
                model_id=descriptor.model_id,
                model_name=descriptor.name,
                specialist_type=descriptor.specialist_type,
                latency_ms=latency_ms,
                img_width=img_width,
                img_height=img_height,
            )

            self.registry.update_model_health(
                descriptor.key,
                status="AVAILABLE",
                latency_ms=latency_ms,
                error=None,
            )
            return parsed

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            err_msg = str(e)
            err_status = "FAILED"

            if "401" in err_msg or "Unauthorized" in err_msg:
                err_status = "UNAUTHORIZED"
            elif "404" in err_msg or "not found" in err_msg.lower():
                err_status = "MODEL_NOT_FOUND"
            elif "timeout" in err_msg.lower():
                err_status = "TIMEOUT"

            logger.warning(
                "Roboflow model %s failed: status=%s latency=%dms",
                descriptor.model_id,
                err_status,
                latency_ms,
            )

            self.registry.update_model_health(
                descriptor.key,
                status=err_status,
                latency_ms=latency_ms,
                error=err_msg[:200],
            )

            return ModelInferenceResult(
                model_id=descriptor.model_id,
                model_key=descriptor.key,
                model_name=descriptor.name,
                specialist_type=descriptor.specialist_type,
                status=err_status,
                latency_ms=latency_ms,
                image_width=img_width,
                image_height=img_height,
                detections=[],
                raw_predictions_count=0,
                error=err_msg[:250],
            )

    def draw_bounding_boxes(
        self,
        img: Image.Image,
        detections: List[ParsedDetection],
    ) -> str:
        """
        Draws bounding boxes and class tags onto the image and returns a base64 Data URL.
        """
        draw_img = img.copy()
        draw = ImageDraw.Draw(draw_img)
        w, h = draw_img.size

        # Simple font handling
        font = None
        try:
            font = ImageFont.load_default()
        except Exception:
            pass

        for det in detections:
            color = CATEGORY_COLORS.get(det.normalized_category, "#D97706")
            box = det.box_pixels
            x1, y1, x2, y2 = box[0], box[1], box[2], box[3]

            # Bounding box rectangle (3px thick)
            draw.rectangle([x1, y1, x2, y2], outline=color, width=3)

            # Label banner
            label = f"{det.raw_class.upper()} {int(det.confidence * 100)}%"
            text_bbox = draw.textbbox((x1, y1 - 16), label, font=font) if font else (x1, y1 - 16, x1 + 100, y1)
            draw.rectangle(
                [text_bbox[0] - 2, text_bbox[1] - 2, text_bbox[2] + 4, text_bbox[3] + 2],
                fill=color,
            )
            draw.text((x1, y1 - 16), label, fill="white", font=font)

        buffered = io.BytesIO()
        draw_img.save(buffered, format="JPEG", quality=88)
        b64_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return f"data:image/jpeg;base64,{b64_str}"

    def analyze(
        self,
        image_bytes: bytes,
        filename: str = "upload.jpg",
        category_hint: Optional[str] = None,
        full_evaluation: bool = False,
    ) -> Dict[str, Any]:
        """
        Executes end-to-end multi-model civic issue analysis.
        """
        # 1. Validate image
        img, img_w, img_h = validate_image_bytes(image_bytes, filename)
        quality_stats = check_image_lighting_and_quality(img)

        # 2. Select models via intelligent routing
        selected_models = self.route_models(category_hint=category_hint, full_evaluation=full_evaluation)

        # 3. Create temporary file for SDK inference
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_path = tmp.name
            img.save(tmp_path, format="JPEG")

        results: List[ModelInferenceResult] = []
        try:
            for descriptor in selected_models:
                res = self.infer_single_model(
                    descriptor=descriptor,
                    temp_img_path=tmp_path,
                    img_width=img_w,
                    img_height=img_h,
                )
                results.append(res)
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

        # 4. Compare predictions & enforce specialist priority
        comparison = RoboflowPredictionComparator.compare(
            results=results,
            category_hint=category_hint,
        )

        # 5. Generate annotated image
        annotated_image_base64 = None
        if comparison.merged_detections:
            annotated_image_base64 = self.draw_bounding_boxes(img, comparison.merged_detections)

        # 6. Format individual model reports
        individual_model_reports = [
            {
                "model_key": r.model_key,
                "model_id": r.model_id,
                "model_name": r.model_name,
                "specialist_type": r.specialist_type,
                "status": r.status,
                "latency_ms": r.latency_ms,
                "raw_detections_count": r.raw_predictions_count,
                "dominant_category": r.dominant_category,
                "max_confidence": r.max_confidence,
                "error": r.error,
                "detections": [
                    {
                        "class": d.raw_class,
                        "category": d.normalized_category,
                        "confidence": d.confidence,
                        "box_relative": d.box_relative,
                        "box_pixels": d.box_pixels,
                    }
                    for d in r.detections
                ],
            }
            for r in results
        ]

        # 7. Formulate descriptive issue summary
        title_cat = comparison.final_category.replace("_", " ").title()
        issue_title = f"{comparison.defect_label.title()} ({title_cat})"
        description = (
            f"Civic defect detected: {comparison.defect_label}. "
            f"Categorized as {title_cat} with {int(comparison.confidence * 100)}% confidence. "
            f"{comparison.comparison_summary}"
        )

        return {
            "predicted_category": comparison.final_category,
            "defect_label": comparison.defect_label,
            "confidence_score": comparison.confidence,
            "consensus_status": comparison.consensus_status,
            "issue_title": issue_title,
            "ai_description": description,
            "annotated_image_base64": annotated_image_base64,
            "comparison": {
                "summary": comparison.comparison_summary,
                "dispute_reason": comparison.dispute_reason,
                "category_breakdown": comparison.category_breakdown,
                "models_executed": comparison.models_executed,
                "models_succeeded": comparison.models_succeeded,
                "requires_human_review": comparison.requires_human_review,
            },
            "detections": [
                {
                    "class": d.raw_class,
                    "category": d.normalized_category,
                    "confidence": d.confidence,
                    "box_relative": d.box_relative,
                    "box_pixels": d.box_pixels,
                    "model_source": d.model_source,
                }
                for d in comparison.merged_detections
            ],
            "individual_models": individual_model_reports,
            "image_quality": quality_stats,
            "mode": "full_evaluation" if full_evaluation else "specialist_routed",
        }

# Global engine instance
roboflow_central_engine = RoboflowCentralEngine()
