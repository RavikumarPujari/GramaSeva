import os
import io
import time
import base64
import logging
import math
from typing import List, Optional, Dict, Any, Tuple
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# Category mapping dictionary for Roboflow civic classes
# Ensures garbage dump is NEVER mistakenly categorized as road damage.
CLASS_CATEGORY_MAP = {
    # Garbage & Solid Waste
    "garbage": "garbage",
    "garbage_dump": "garbage",
    "trash": "garbage",
    "waste": "garbage",
    "litter": "garbage",
    "dump": "garbage",
    "debris": "garbage",
    "plastic_waste": "garbage",
    "solid_waste": "garbage",
    "rubbish": "garbage",
    "dumpster": "garbage",
    # Road Damage & Potholes
    "pothole": "road_damage",
    "potholes": "road_damage",
    "road_damage": "road_damage",
    "crack": "road_damage",
    "cracks": "road_damage",
    "road_crack": "road_damage",
    "broken_road": "road_damage",
    "damaged_road": "road_damage",
    "asphalt_damage": "road_damage",
    "d00": "road_damage",  # Longitudinal crack
    "d10": "road_damage",  # Transverse crack
    "d20": "road_damage",  # Alligator crack
    "d40": "road_damage",  # Pothole
    # Water Supply & Pipeline Leaks
    "water_leak": "water_leak",
    "leak": "water_leak",
    "pipeline_leak": "water_leak",
    "pipe_burst": "water_leak",
    "burst_pipe": "water_leak",
    "broken_pipe": "water_leak",
    "pipe_leak": "water_leak",
    # Drainage & Waterlogging
    "drain": "drainage",
    "drainage": "drainage",
    "open_drain": "drainage",
    "clogged_drain": "drainage",
    "sewage": "drainage",
    "sewer": "drainage",
    "waterlogging": "drainage",
    "standing_water": "drainage",
    "stagnant_water": "drainage",
    "overflowing_drain": "drainage",
    # Streetlight & Electrical
    "streetlight": "streetlight",
    "broken_streetlight": "streetlight",
    "dark_street": "streetlight",
    "electric_pole": "streetlight",
    "street_light": "streetlight",
    # Public Facilities
    "public_facility": "public_facility",
    "broken_bench": "public_facility",
    "damaged_wall": "public_facility",
}


def compute_box_iou(box1: List[float], box2: List[float]) -> float:
    """
    Computes Intersection over Union (IoU) of two bounding boxes in [xmin, ymin, xmax, ymax] format.
    """
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    inter_w = max(0.0, x2 - x1)
    inter_h = max(0.0, y2 - y1)
    inter_area = inter_w * inter_h

    area1 = max(0.0, box1[2] - box1[0]) * max(0.0, box1[3] - box1[1])
    area2 = max(0.0, box2[2] - box2[0]) * max(0.0, box2[3] - box2[1])
    union_area = area1 + area2 - inter_area

    if union_area <= 0:
        return 0.0
    return inter_area / union_area


class RoboflowInferenceService:
    """
    Dedicated, multi-model inference and consensus service for Roboflow Object Detection models.
    Supports 3 independent Roboflow models:
      - Model 1: civic_issues_v1-dc7ae-zzdgj/1 (YOLOv11 Object Detection)
      - Model 2: civic-issue-yljwt-tptzy/2 (Object Detection)
      - Model 3: civic-issues-qj5pb/2 (Object Detection)
    Inference API: https://serverless.roboflow.com
    SDK: inference-sdk (header-based auth)
    """

    def __init__(self):
        self._client = None
        self._cached_api_key = None
        self._cached_api_url = None
        self.default_api_url = "https://serverless.roboflow.com"
        self.default_model_garbage = "garbage_detection-wvzwv-n8vsv/1"
        self.default_model_road = "road-damage-detection-fn0qh/1"
        self.default_model_waterlogging = "water-logging-a7zhi/1"
        self.default_model_civic_1 = "civic-issues-lroee/3"
        self.default_model_civic_2 = "civic-issues-nq7sy-bh8t3/1"
        self.max_file_size_bytes = 10 * 1024 * 1024  # 10 MB
        self.supported_mime_types = {"image/jpeg", "image/png", "image/webp"}
        self.min_confidence_threshold = 0.25

    def _get_api_key(self) -> Optional[str]:
        """Reads API key from environment variables without logging or exposing it."""
        key = os.environ.get("ROBOFLOW_API_KEY", "").strip()
        if not key or key == "YOUR_NEW_PRIVATE_KEY" or key == "your_roboflow_api_key_here":
            return None
        return key

    def _get_api_url(self) -> str:
        return os.environ.get("ROBOFLOW_API_URL", self.default_api_url).strip() or self.default_api_url

    def get_registered_models(self) -> List[Dict[str, str]]:
        """Returns the Five Exact Roboflow Models (Part 2)."""
        m_garbage = os.environ.get("ROBOFLOW_MODEL_GARBAGE", "").strip() or self.default_model_garbage
        m_road = os.environ.get("ROBOFLOW_MODEL_ROAD", "").strip() or self.default_model_road
        m_water = os.environ.get("ROBOFLOW_MODEL_WATERLOGGING", "").strip() or self.default_model_waterlogging
        m_c1 = os.environ.get("ROBOFLOW_MODEL_CIVIC_1", "").strip() or self.default_model_civic_1
        m_c2 = os.environ.get("ROBOFLOW_MODEL_CIVIC_2", "").strip() or self.default_model_civic_2
        return [
            {"key": "garbage", "name": "Model 1 (Garbage Detection)", "model_id": m_garbage, "specialist": "garbage"},
            {"key": "road", "name": "Model 2 (Road Damage Detection)", "model_id": m_road, "specialist": "road_damage"},
            {"key": "waterlogging", "name": "Model 3 (Waterlogging Detection)", "model_id": m_water, "specialist": "drainage"},
            {"key": "civic_1", "name": "Model 4 (Civic Issues Detection)", "model_id": m_c1, "specialist": "general_civic"},
            {"key": "civic_2", "name": "Model 5 (Civic Issues Detection 2)", "model_id": m_c2, "specialist": "general_civic"},
        ]

    def _get_or_create_client(self, api_key: str, api_url: str):
        """Reuses InferenceHTTPClient safely across requests with header authentication."""
        if self._client is None or self._cached_api_key != api_key or self._cached_api_url != api_url:
            from inference_sdk import InferenceHTTPClient, InferenceConfiguration
            self._client = InferenceHTTPClient(
                api_url=api_url,
                api_key=api_key,
            ).configure(InferenceConfiguration(
                api_key_transport="header"
            ))
            self._cached_api_key = api_key
            self._cached_api_url = api_url
        return self._client

    def validate_image_bytes(self, image_bytes: bytes) -> Tuple[bool, Optional[str], Optional[Image.Image]]:
        """Validates file size, formats (JPEG, PNG, WebP) and verifies the image is not corrupted."""
        if not image_bytes:
            return False, "Image file is empty.", None

        if len(image_bytes) > self.max_file_size_bytes:
            return False, f"Image file exceeds maximum allowed size of {self.max_file_size_bytes // (1024*1024)} MB.", None

        try:
            img = Image.open(io.BytesIO(image_bytes))
            img.verify()
            img = Image.open(io.BytesIO(image_bytes))
            if img.format not in ("JPEG", "PNG", "WEBP", "MPO"):
                return False, f"Unsupported image format: {img.format}. Please upload JPEG, PNG, or WebP.", None
            return True, None, img
        except Exception as e:
            return False, f"Corrupted or invalid image file: {str(e)}", None

    def map_class_to_category(self, class_name: str) -> str:
        """
        Maps model output class to GramaSeva civic category.
        CRITICAL GOVERNANCE RULE: Garbage dump must NEVER be forced into road damage.
        """
        clean_name = class_name.lower().replace("-", "_").strip()
        if clean_name in CLASS_CATEGORY_MAP:
            return CLASS_CATEGORY_MAP[clean_name]

        # Explicit garbage matching first
        if any(w in clean_name for w in ("garbage", "waste", "trash", "litter", "dump", "debris", "rubbish")):
            return "garbage"
        # Road damage matching
        if any(w in clean_name for w in ("pothole", "crack", "pavement", "asphalt", "road")):
            return "road_damage"
        # Water leak matching
        if any(w in clean_name for w in ("pipe", "leak", "water_burst")):
            return "water_leak"
        # Drainage matching
        if any(w in clean_name for w in ("drain", "sewer", "sewage", "gutter", "waterlog")):
            return "drainage"
        # Streetlight matching
        if any(w in clean_name for w in ("light", "lamp", "electric", "pole")):
            return "streetlight"

        return "other"

    def select_primary_category(self, predictions: List[Dict[str, Any]]) -> Tuple[Optional[str], Optional[str], Optional[float]]:
        """
        Selects primary category from multiple detections for a single model:
        1. Filters predictions above minimum confidence threshold.
        2. Sorts primarily by confidence, secondarily by area.
        3. Returns mapped category, top class name, and confidence.
        """
        valid = [p for p in predictions if float(p.get("confidence", 0.0)) >= self.min_confidence_threshold]
        if not valid:
            return None, None, None

        sorted_preds = sorted(
            valid,
            key=lambda p: (
                float(p.get("confidence", 0.0)),
                float(p.get("width", 0.0)) * float(p.get("height", 0.0))
            ),
            reverse=True,
        )

        top = sorted_preds[0]
        top_class = str(top.get("class", "civic_issue"))
        top_conf = round(float(top.get("confidence", 0.0)), 3)
        primary_cat = self.map_class_to_category(top_class)
        return primary_cat, top_class, top_conf

    def infer_single_model(
        self,
        model_id: str,
        model_alias: str,
        pil_img: Image.Image,
        image_path: Optional[str] = None,
        village_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Runs inference for one model with independent error/timeout protection.
        Does NOT block or throw if one model fails.
        """
        start_time = time.perf_counter()
        api_key = self._get_api_key()
        api_url = self._get_api_url()

        if not api_key:
            return {
                "model_key": model_alias,
                "model_id": model_id,
                "status": "UNAVAILABLE",
                "error": "ROBOFLOW_API_KEY environment variable is not configured or uses placeholder.",
                "predictions": [],
                "primary_category": None,
                "defect_label": None,
                "confidence_score": None,
                "latency_ms": int((time.perf_counter() - start_time) * 1000),
            }

        try:
            client = self._get_or_create_client(api_key, api_url)
            if image_path and os.path.exists(image_path):
                raw_result = client.infer(image_path, model_id=model_id)
            else:
                raw_result = client.infer(pil_img, model_id=model_id)

            latency_ms = int((time.perf_counter() - start_time) * 1000)
            predictions = []
            if isinstance(raw_result, dict):
                raw_preds = raw_result.get("predictions", [])
                if isinstance(raw_preds, list):
                    predictions = raw_preds

            primary_cat, top_label, top_conf = self.select_primary_category(predictions)
            status = "COMPLETED" if (primary_cat and len(predictions) > 0) else "NO_DETECTIONS"

            return {
                "model_key": model_alias,
                "model_id": model_id,
                "status": status,
                "predictions": predictions,
                "primary_category": primary_cat,
                "defect_label": top_label,
                "confidence_score": top_conf,
                "latency_ms": latency_ms,
                "error": None,
            }

        except Exception as e:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            err_str = str(e)
            if api_key and api_key in err_str:
                err_str = err_str.replace(api_key, "[REDACTED_API_KEY]")
            logger.warning(f"Roboflow model {model_id} failed or timed out: {err_str}")
            return {
                "model_key": model_alias,
                "model_id": model_id,
                "status": "UNAVAILABLE",
                "error": err_str,
                "predictions": [],
                "primary_category": None,
                "defect_label": None,
                "confidence_score": None,
                "latency_ms": latency_ms,
            }

    def compare_predictions(
        self,
        model_results: List[Dict[str, Any]],
        img_width: int = 640,
        img_height: int = 480,
    ) -> Dict[str, Any]:
        """
        Intelligent multi-model comparison:
        1. Compares categories predicted across the 3 models.
        2. Groups spatial bounding boxes by IoU overlap across models.
        3. Identifies:
           - agreed_predictions: categories detected by >= 2 models
           - model_specific_predictions: categories found by only 1 model
           - conflicting_predictions: differing categories between models
           - uncertain_results: low confidence or disputed
        4. Calculates consensus status:
           - "STRONG_CONSENSUS": All active models agree (or 2/2 agreeing with high confidence).
           - "MAJORITY_CONSENSUS": 2 out of 3 models agree on category.
           - "DISPUTED": Different models predict conflicting categories (e.g., Road Damage vs Garbage).
           - "SINGLE_MODEL_DETECTION": Only 1 model found detections.
           - "NO_DETECTIONS": None of the models found detections.
           - "UNAVAILABLE": All models offline or unconfigured.
        """
        active_results = [r for r in model_results if r.get("status") == "COMPLETED" and r.get("primary_category")]
        all_unavailable = all(r.get("status") in ("UNAVAILABLE", "ERROR") for r in model_results)
        all_no_detections = all(r.get("status") == "NO_DETECTIONS" for r in model_results)

        if all_unavailable:
            return {
                "consensus_status": "UNAVAILABLE",
                "has_consensus": False,
                "consensus_category": None,
                "consensus_confidence": None,
                "defect_label": None,
                "agreed_predictions": [],
                "model_specific_predictions": [],
                "conflicting_predictions": [],
                "uncertain_results": True,
                "dispute_reason": "All 3 Roboflow models are currently offline or unconfigured.",
                "models_evaluated": len(model_results),
                "models_succeeded": 0,
            }

        if all_no_detections or not active_results:
            return {
                "consensus_status": "NO_DETECTIONS",
                "has_consensus": False,
                "consensus_category": None,
                "consensus_confidence": None,
                "defect_label": None,
                "agreed_predictions": [],
                "model_specific_predictions": [],
                "conflicting_predictions": [],
                "uncertain_results": True,
                "dispute_reason": "No civic defects detected above threshold by any of the 3 models.",
                "models_evaluated": len(model_results),
                "models_succeeded": len([r for r in model_results if r.get("status") in ("COMPLETED", "NO_DETECTIONS")]),
            }

        # Category frequency count
        category_counts: Dict[str, List[Dict[str, Any]]] = {}
        for res in active_results:
            cat = res["primary_category"]
            category_counts.setdefault(cat, []).append(res)

        agreed_predictions = []
        model_specific_predictions = []
        conflicting_predictions = []

        # Find categories supported by >= 2 models
        for cat, group in category_counts.items():
            if len(group) >= 2:
                avg_conf = sum(float(g.get("confidence_score") or 0.0) for g in group) / len(group)
                agreed_predictions.append({
                    "category": cat,
                    "models": [g.get("model_key") for g in group],
                    "model_ids": [g.get("model_id") for g in group],
                    "count": len(group),
                    "average_confidence": round(avg_conf, 3),
                })
            else:
                g = group[0]
                model_specific_predictions.append({
                    "category": cat,
                    "model": g.get("model_key"),
                    "model_id": g.get("model_id"),
                    "confidence": g.get("confidence_score"),
                    "defect_label": g.get("defect_label"),
                })

        # Identify conflicts (multiple different categories predicted)
        has_multiple_categories = len(category_counts) > 1
        dispute_reason = None

        if has_multiple_categories:
            cats = list(category_counts.keys())
            for cat in cats:
                models_for_cat = [g.get("model_key") for g in category_counts[cat]]
                conflicting_predictions.append({
                    "category": cat,
                    "models": models_for_cat,
                    "confidences": [g.get("confidence_score") for g in category_counts[cat]],
                })
            dispute_reason = f"Models disagree on issue category: {', '.join(cats)}. Manual citizen confirmation required."

        # Determine consensus status & primary consensus category
        consensus_status = "DISPUTED"
        has_consensus = False
        consensus_category = None
        consensus_confidence = None
        top_defect_label = None

        if len(agreed_predictions) > 0:
            # Sort agreed categories by model count then confidence
            agreed_sorted = sorted(agreed_predictions, key=lambda a: (a["count"], a["average_confidence"]), reverse=True)
            top_agreement = agreed_sorted[0]
            consensus_category = top_agreement["category"]
            consensus_confidence = top_agreement["average_confidence"]
            has_consensus = True

            # If all active models agree
            if top_agreement["count"] == len(active_results) and len(active_results) >= 2:
                consensus_status = "STRONG_CONSENSUS"
            else:
                consensus_status = "MAJORITY_CONSENSUS"

            # Top defect label from the agreeing models
            for r in category_counts.get(consensus_category, []):
                if r.get("defect_label"):
                    top_defect_label = r["defect_label"]
                    break

        elif len(active_results) == 1:
            # Only 1 model produced active detection
            single = active_results[0]
            consensus_status = "SINGLE_MODEL_DETECTION"
            has_consensus = False
            consensus_category = single.get("primary_category")
            consensus_confidence = single.get("confidence_score")
            top_defect_label = single.get("defect_label")
        else:
            # Multiple active models, each predicting different categories (dispute)
            consensus_status = "DISPUTED"
            has_consensus = False
            # Pick highest confidence detection as suggested default, but flag dispute
            highest_conf_res = max(active_results, key=lambda r: float(r.get("confidence_score") or 0.0))
            consensus_category = highest_conf_res.get("primary_category")
            consensus_confidence = highest_conf_res.get("confidence_score")
            top_defect_label = highest_conf_res.get("defect_label")

        return {
            "consensus_status": consensus_status,
            "has_consensus": has_consensus,
            "consensus_category": consensus_category,
            "consensus_confidence": consensus_confidence,
            "defect_label": top_defect_label,
            "agreed_predictions": agreed_predictions,
            "model_specific_predictions": model_specific_predictions,
            "conflicting_predictions": conflicting_predictions,
            "uncertain_results": not has_consensus or (consensus_confidence is not None and consensus_confidence < 0.40),
            "dispute_reason": dispute_reason,
            "models_evaluated": len(model_results),
            "models_succeeded": len(active_results),
        }

    def draw_bounding_boxes(
        self,
        image: Image.Image,
        predictions: List[Dict[str, Any]],
    ) -> str:
        """
        Backward-compatible single-model bounding box renderer.
        If no predictions provided, returns clean base64 image data URI without artificial boxes.
        """
        valid = [p for p in predictions if float(p.get("confidence", 0.0)) >= self.min_confidence_threshold]
        return self.draw_multi_model_bounding_boxes(
            image=image,
            model_results=[{"model_key": "model_1", "predictions": valid}],
        )

    def draw_multi_model_bounding_boxes(
        self,
        image: Image.Image,
        model_results: List[Dict[str, Any]],
    ) -> str:
        """
        Renders real bounding boxes from all 3 models with model attribution tags.
        Merges duplicate bounding boxes of the same category with IoU >= 0.45 into combined tags (e.g. [M1+M2]).
        Returns data:image/jpeg;base64 URI.
        """
        annotated = image.copy().convert("RGB")
        draw = ImageDraw.Draw(annotated)
        img_w, img_h = annotated.size

        # Category color coding
        color_map = {
            "road_damage": "#EF4444",   # Red
            "garbage": "#F59E0B",       # Amber / Orange
            "water_leak": "#0284C7",    # Sky Blue
            "drainage": "#10B981",      # Emerald Green
            "streetlight": "#8B5CF6",   # Purple
            "other": "#EC4899",         # Pink
        }

        # Step 1: Collect all raw boxes with model attribution
        raw_boxes = []
        model_aliases = {
            "model_1": "M1",
            "model_2": "M2",
            "model_3": "M3",
        }

        for res in model_results:
            m_key = res.get("model_key", "model_1")
            m_tag = model_aliases.get(m_key, m_key[:2].upper())
            for p in res.get("predictions", []):
                conf = float(p.get("confidence", 0.0))
                if conf < self.min_confidence_threshold:
                    continue

                cx = float(p.get("x", 0.0))
                cy = float(p.get("y", 0.0))
                w = float(p.get("width", 0.0))
                h = float(p.get("height", 0.0))
                cls_name = str(p.get("class", "defect"))
                cat = self.map_class_to_category(cls_name)

                xmin = max(0.0, cx - w / 2.0)
                ymin = max(0.0, cy - h / 2.0)
                xmax = min(float(img_w), cx + w / 2.0)
                ymax = min(float(img_h), cy + h / 2.0)

                raw_boxes.append({
                    "box": [xmin, ymin, xmax, ymax],
                    "category": cat,
                    "class_name": cls_name,
                    "confidence": conf,
                    "model_tags": [m_tag],
                })

        if not raw_boxes:
            buffer = io.BytesIO()
            annotated.save(buffer, format="JPEG", quality=88)
            b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
            return f"data:image/jpeg;base64,{b64}"

        # Step 2: Merge overlapping boxes of same category (IoU >= 0.40)
        merged_boxes: List[Dict[str, Any]] = []
        for item in raw_boxes:
            merged = False
            for target in merged_boxes:
                if target["category"] == item["category"]:
                    iou = compute_box_iou(target["box"], item["box"])
                    if iou >= 0.40:
                        # Union box coordinates
                        target["box"] = [
                            min(target["box"][0], item["box"][0]),
                            min(target["box"][1], item["box"][1]),
                            max(target["box"][2], item["box"][2]),
                            max(target["box"][3], item["box"][3]),
                        ]
                        # Merge model tags
                        for t in item["model_tags"]:
                            if t not in target["model_tags"]:
                                target["model_tags"].append(t)
                        # Keep maximum confidence
                        if item["confidence"] > target["confidence"]:
                            target["confidence"] = item["confidence"]
                            target["class_name"] = item["class_name"]
                        merged = True
                        break
            if not merged:
                merged_boxes.append(item)

        # Step 3: Draw boxes and attribution badges
        for item in merged_boxes:
            box = item["box"]
            cat = item["category"]
            cls_name = item["class_name"]
            conf = item["confidence"]
            tags = "+".join(sorted(item["model_tags"]))
            box_color = color_map.get(cat, "#EF4444")

            xmin, ymin, xmax, ymax = box

            # 3-pixel stroke
            for offset in range(3):
                draw.rectangle(
                    [xmin - offset, ymin - offset, xmax + offset, ymax + offset],
                    outline=box_color,
                )

            # Attribution tag text: e.g. "[M1+M2] POTHOLE 89%"
            label_text = f"[{tags}] {cls_name.upper()} {int(conf * 100)}%"
            label_y = max(0.0, ymin - 22)
            draw.rectangle(
                [xmin, label_y, xmin + len(label_text) * 8 + 12, label_y + 20],
                fill=box_color,
            )
            draw.text((xmin + 5, label_y + 3), label_text, fill="white")

        buffer = io.BytesIO()
        annotated.save(buffer, format="JPEG", quality=88)
        b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return f"data:image/jpeg;base64,{b64}"

    def analyze_multi_model(
        self,
        image_input: Any,  # bytes, file path, or PIL Image
        village_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes multi-model inference across Model 1, Model 2, and Model 3.
        Runs intelligent comparison, IoU overlap analysis, and generates annotated image.
        Returns unified multi-model result.
        """
        start_time = time.perf_counter()

        # Step 1: Validate input image
        if isinstance(image_input, (str, os.PathLike)):
            if not os.path.exists(image_input):
                return {
                    "status": "ERROR",
                    "error": f"Image file not found: {image_input}",
                    "model_provider": "roboflow-multi-model",
                    "model_summaries": [],
                    "comparison": None,
                    "latency_ms": 0,
                    "requires_human_review": True,
                }
            with open(image_input, "rb") as f:
                image_bytes = f.read()
            image_path_for_client = str(image_input)
        elif isinstance(image_input, bytes):
            image_bytes = image_input
            image_path_for_client = None
        else:
            return {
                "status": "ERROR",
                "error": "Invalid image input type. Expected bytes or file path.",
                "model_provider": "roboflow-multi-model",
                "model_summaries": [],
                "comparison": None,
                "latency_ms": 0,
                "requires_human_review": True,
            }

        valid, error_msg, pil_img = self.validate_image_bytes(image_bytes)
        if not valid or pil_img is None:
            return {
                "status": "INVALID_IMAGE",
                "error": error_msg or "Invalid image file",
                "model_provider": "roboflow-multi-model",
                "model_summaries": [],
                "comparison": None,
                "latency_ms": int((time.perf_counter() - start_time) * 1000),
                "requires_human_review": True,
            }

        # Step 2: Get registered 3 models
        registered_models = self.get_registered_models()
        model_results = []

        # Step 3: Run inference on each model independently
        for m in registered_models:
            m_res = self.infer_single_model(
                model_id=m["model_id"],
                model_alias=m["key"],
                pil_img=pil_img,
                image_path=image_path_for_client,
                village_name=village_name,
            )
            m_res["model_name"] = m["name"]
            model_results.append(m_res)

        # Step 4: Run intelligent comparison
        comparison = self.compare_predictions(
            model_results=model_results,
            img_width=pil_img.size[0],
            img_height=pil_img.size[1],
        )

        # Step 5: Draw multi-model bounding boxes with model attribution
        annotated_b64 = None
        has_any_detection = any(len(r.get("predictions", [])) > 0 for r in model_results)
        if has_any_detection:
            annotated_b64 = self.draw_multi_model_bounding_boxes(pil_img, model_results)

        # Step 6: Formulate human-readable description and title
        consensus_status = comparison["consensus_status"]
        consensus_cat = comparison["consensus_category"] or "road_damage"
        top_label = comparison["defect_label"] or consensus_cat.replace("_", " ")
        consensus_conf = comparison["consensus_confidence"]

        if consensus_status in ("STRONG_CONSENSUS", "MAJORITY_CONSENSUS"):
            issue_title = f"{top_label.upper()} in {village_name or 'Village'}"
            agreed_count = len(comparison.get("agreed_predictions", [{}])[0].get("models", []))
            ai_description = (
                f"Multi-model AI consensus ({agreed_count}/3 models agree): "
                f"Detected {top_label} ({consensus_cat.replace('_', ' ')}) with {int((consensus_conf or 0) * 100)}% confidence at {village_name or 'reported location'}."
            )
            overall_status = "COMPLETED"
        elif consensus_status == "DISPUTED":
            issue_title = f"Civic Issue at {village_name or 'Village'} (Classification Disputed)"
            ai_description = (
                f"AI Classification Disputed: Models detected different issues ({comparison.get('dispute_reason')}). "
                f"Please manually select the correct civic category."
            )
            overall_status = "DISPUTED"
        elif consensus_status == "SINGLE_MODEL_DETECTION":
            issue_title = f"{top_label.upper()} in {village_name or 'Village'}"
            ai_description = (
                f"Single-model detection: Detected {top_label} ({consensus_cat.replace('_', ' ')}) with {int((consensus_conf or 0) * 100)}% confidence. "
                f"Pending citizen confirmation."
            )
            overall_status = "COMPLETED"
        elif consensus_status == "NO_DETECTIONS":
            issue_title = f"Civic Issue at {village_name or 'Village'}"
            ai_description = (
                f"All 3 models inspected the photograph. No prominent defect identified with sufficient confidence. "
                f"Please confirm category and describe the problem."
            )
            overall_status = "NO_DETECTIONS"
        else:
            issue_title = f"Reported Issue at {village_name or 'Village'}"
            ai_description = f"AI inspection service currently unconfigured or offline. Falling back to local verification."
            overall_status = "UNAVAILABLE"

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        # Model summaries list for easy consumption by frontend and DB
        model_summaries = []
        for r in model_results:
            model_summaries.append({
                "model_key": r.get("model_key"),
                "model_name": r.get("model_name"),
                "model_id": r.get("model_id"),
                "status": r.get("status"),
                "primary_category": r.get("primary_category"),
                "defect_label": r.get("defect_label"),
                "confidence_score": r.get("confidence_score"),
                "detections_count": len(r.get("predictions", [])),
                "latency_ms": r.get("latency_ms", 0),
                "error": r.get("error"),
            })

        return {
            "status": overall_status,
            "model_provider": "roboflow-multi-model",
            "model_summaries": model_summaries,
            "comparison": comparison,
            "primary_category": consensus_cat,
            "defect_label": top_label,
            "confidence_score": consensus_conf,
            "issue_title": issue_title,
            "ai_description": ai_description,
            "annotated_image_base64": annotated_b64,
            "latency_ms": latency_ms,
            "requires_human_review": True,
            "raw_model_results": model_results,
        }

    # Preserved backward-compatible analyze_image method for single model calls
    def analyze_image(
        self,
        image_input: Any,
        village_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Backward compatible single-model inference (Model 1 default).
        """
        registered = self.get_registered_models()
        m1_id = registered[0]["model_id"]

        valid, error_msg, pil_img = self.validate_image_bytes(
            image_input if isinstance(image_input, bytes) else open(image_input, "rb").read()
        )
        if not valid or pil_img is None:
            return {
                "status": "INVALID_IMAGE",
                "error": error_msg or "Invalid image file",
                "model_provider": "roboflow",
                "model_id": m1_id,
                "predictions": [],
                "latency_ms": 0,
                "requires_human_review": True,
            }

        res = self.infer_single_model(
            model_id=m1_id,
            model_alias="model_1",
            pil_img=pil_img,
            village_name=village_name,
        )

        annotated_b64 = None
        if len(res.get("predictions", [])) > 0:
            annotated_b64 = self.draw_multi_model_bounding_boxes(pil_img, [res])

        cat = res.get("primary_category")
        lbl = res.get("defect_label")
        conf = res.get("confidence_score")

        return {
            "status": res.get("status"),
            "model_provider": "roboflow",
            "model_id": m1_id,
            "predictions": res.get("predictions", []),
            "primary_category": cat,
            "defect_label": lbl,
            "confidence_score": conf,
            "issue_title": f"{lbl.upper()} in {village_name or 'Village'}" if lbl else f"Civic Issue at {village_name or 'Village'}",
            "ai_description": f"Detected {lbl} ({cat}) with {int((conf or 0)*100)}% confidence." if lbl else "No defect detected above threshold.",
            "annotated_image_base64": annotated_b64,
            "latency_ms": res.get("latency_ms", 0),
            "requires_human_review": True,
            "error": res.get("error"),
        }


# Global singleton service
roboflow_service = RoboflowInferenceService()
