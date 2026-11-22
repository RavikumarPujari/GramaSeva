from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from app.services.roboflow.result_parser import ModelInferenceResult, ParsedDetection

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

@dataclass
class AggregatedComparison:
    final_category: str
    defect_label: str
    confidence: float
    consensus_status: str  # STRONG_CONSENSUS, SPECIALIST_CONFIRMED, MULTI_ISSUE_DETECTED, UNCERTAIN_DISPUTE, NO_RELIABLE_DETECTION, MANUAL_REVIEW_REQUIRED
    comparison_summary: str
    dispute_reason: Optional[str] = None
    all_detections: List[ParsedDetection] = field(default_factory=list)
    merged_detections: List[ParsedDetection] = field(default_factory=list)
    category_breakdown: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    models_executed: int = 0
    models_succeeded: int = 0
    requires_human_review: bool = True

class RoboflowPredictionComparator:
    """
    Accurately compares predictions across all executed Roboflow models.
    Enforces specialist domain authority:
      - Garbage specialist predictions remain classified as garbage.
      - Road damage specialist predictions remain classified as road damage.
      - Waterlogging specialist predictions remain classified as drainage.
    Eliminates false overrides caused by arbitrary uncalibrated confidence scores.
    """

    @staticmethod
    def compare(
        results: List[ModelInferenceResult],
        category_hint: Optional[str] = None,
    ) -> AggregatedComparison:
        succeeded = [r for r in results if r.status in ("COMPLETED", "NO_DETECTIONS")]
        active_results = [r for r in succeeded if r.detections]

        if not active_results:
            return AggregatedComparison(
                final_category=category_hint or "road_damage",
                defect_label="No Confident Detection",
                confidence=0.0,
                consensus_status="NO_RELIABLE_DETECTION",
                comparison_summary="No civic defects detected above confidence threshold by executed models.",
                requires_human_review=True,
                models_executed=len(results),
                models_succeeded=len(succeeded),
            )

        # 1. Aggregate all detections & group by normalized category
        all_detections: List[ParsedDetection] = []
        category_detections: Dict[str, List[ParsedDetection]] = {}

        for r in active_results:
            for d in r.detections:
                all_detections.append(d)
                cat = d.normalized_category
                if cat not in category_detections:
                    category_detections[cat] = []
                category_detections[cat].append(d)

        # 2. Build category breakdown
        breakdown: Dict[str, Dict[str, Any]] = {}
        for cat, dets in category_detections.items():
            max_conf = max(d.confidence for d in dets)
            sources = list(set(d.model_source for d in dets))
            breakdown[cat] = {
                "count": len(dets),
                "max_confidence": round(max_conf, 4),
                "model_sources": sources,
            }

        # 3. Check for Specialist Priority
        # Garbage specialist has authority for garbage dumps
        garbage_result = next((r for r in active_results if r.model_key == "garbage" and r.detections), None)
        road_result = next((r for r in active_results if r.model_key == "road" and r.detections), None)
        water_result = next((r for r in active_results if r.model_key == "waterlogging" and r.detections), None)

        # 4. Multi-issue check: e.g. Garbage dumped beside a damaged road or waterlogged pothole
        has_garbage = bool("garbage" in category_detections)
        has_road = bool("road_damage" in category_detections)
        has_water = bool("drainage" in category_detections)

        # 5. Spatial IoU Deduplication & Merging
        # If two models detect the same object at the same spot (IoU > 0.40):
        # Give preference to the specialist model over general models.
        merged_detections: List[ParsedDetection] = []
        sorted_all = sorted(
            all_detections,
            key=lambda d: (
                1.0 if d.model_source in ("garbage", "road", "waterlogging") else 0.5,
                d.confidence,
            ),
            reverse=True,
        )

        for candidate in sorted_all:
            overlap = False
            for kept in merged_detections:
                iou = compute_box_iou(candidate.box_pixels, kept.box_pixels)
                if iou > 0.40:
                    overlap = True
                    break
            if not overlap:
                merged_detections.append(candidate)

        # 6. Consensus & Dispute Evaluation
        final_category = "road_damage"
        defect_label = "Civic Issue"
        confidence = 0.5
        consensus_status = "SPECIALIST_CONFIRMED"
        dispute_reason = None
        summary = ""

        # Case A: Multiple distinct issues detected
        if (has_garbage and has_road) or (has_water and has_road):
            # Check spatial separation: are bounding boxes separate?
            separate_spatial_issues = True
            for g_det in category_detections.get("garbage", []):
                for r_det in category_detections.get("road_damage", []):
                    if compute_box_iou(g_det.box_pixels, r_det.box_pixels) > 0.60:
                        separate_spatial_issues = False
                        break

            if separate_spatial_issues:
                # True multi-issue scenario
                final_category = category_hint if category_hint in ("garbage", "road_damage", "drainage") else (
                    "garbage" if has_garbage and garbage_result else "road_damage"
                )
                defect_label = "Multiple Issues (Garbage & Road Damage)"
                confidence = round(max(d.confidence for d in all_detections), 4)
                consensus_status = "MULTI_ISSUE_DETECTED"
                summary = "Multiple distinct civic issues identified: Garbage accumulation and Road surface damage."
                dispute_reason = "Both garbage dump and road damage detected at separate spatial locations in photograph."
            else:
                # Contradictory classification of the SAME object (The garbage dump vs road damage bug!)
                # Specialist Domain Rule: Garbage specialist takes precedence on garbage heaps.
                if garbage_result and garbage_result.max_confidence >= 0.35:
                    final_category = "garbage"
                    defect_label = garbage_result.detections[0].raw_class
                    confidence = garbage_result.max_confidence
                    consensus_status = "SPECIALIST_CONFIRMED"
                    summary = "Garbage specialist confirmed solid waste accumulation. Overrode conflicting general class."
                elif road_result and road_result.max_confidence >= 0.35:
                    final_category = "road_damage"
                    defect_label = road_result.detections[0].raw_class
                    confidence = road_result.max_confidence
                    consensus_status = "SPECIALIST_CONFIRMED"
                    summary = "Road specialist confirmed road surface damage/pothole."
                else:
                    final_category = category_hint or "garbage"
                    defect_label = "Uncertain Civic Issue"
                    confidence = 0.45
                    consensus_status = "UNCERTAIN_DISPUTE"
                    dispute_reason = "Models produced conflicting classifications on the same bounding region. Requires human confirmation."
                    summary = "Conflicting classifications between garbage and road damage on the same defect area."

        # Case B: Strong Consensus across 2+ models
        elif len(category_detections) == 1:
            cat = list(category_detections.keys())[0]
            models_agreeing = len(set(d.model_source for d in category_detections[cat]))
            final_category = cat
            top_det = category_detections[cat][0]
            defect_label = top_det.raw_class
            confidence = top_det.confidence

            if models_agreeing >= 2:
                consensus_status = "STRONG_CONSENSUS"
                summary = f"Strong multi-model consensus: {models_agreeing} models confirmed {cat.replace('_', ' ')}."
            else:
                consensus_status = "SPECIALIST_CONFIRMED"
                summary = f"Confirmed by {top_det.model_source} specialist with confidence {round(confidence * 100)}%."

        # Case C: Single specialist active
        elif garbage_result and garbage_result.max_confidence >= 0.35:
            final_category = "garbage"
            defect_label = garbage_result.detections[0].raw_class
            confidence = garbage_result.max_confidence
            consensus_status = "SPECIALIST_CONFIRMED"
            summary = "Garbage specialist identified solid waste dump."

        elif road_result and road_result.max_confidence >= 0.35:
            final_category = "road_damage"
            defect_label = road_result.detections[0].raw_class
            confidence = road_result.max_confidence
            consensus_status = "SPECIALIST_CONFIRMED"
            summary = "Road specialist identified road damage / pothole."

        elif water_result and water_result.max_confidence >= 0.35:
            final_category = "drainage"
            defect_label = water_result.detections[0].raw_class
            confidence = water_result.max_confidence
            consensus_status = "SPECIALIST_CONFIRMED"
            summary = "Waterlogging specialist identified standing water accumulation."

        else:
            # Fallback to highest confidence detection
            top_det = sorted_all[0]
            final_category = top_det.normalized_category
            defect_label = top_det.raw_class
            confidence = top_det.confidence
            consensus_status = "SPECIALIST_CONFIRMED"
            summary = f"Identified {top_det.raw_class} by {top_det.model_source}."

        return AggregatedComparison(
            final_category=final_category,
            defect_label=defect_label,
            confidence=confidence,
            consensus_status=consensus_status,
            comparison_summary=summary,
            dispute_reason=dispute_reason,
            all_detections=all_detections,
            merged_detections=merged_detections,
            category_breakdown=breakdown,
            models_executed=len(results),
            models_succeeded=len(succeeded),
            requires_human_review=True,
        )
