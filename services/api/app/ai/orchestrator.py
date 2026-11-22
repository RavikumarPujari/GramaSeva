import io
import os
import sys
import time
import json
import uuid
import math
import base64
from typing import Optional, Dict, Any, List
from PIL import Image, ImageDraw
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.issues import Issue, Submission, ModelRun, MediaAsset
from app.ai.gemini_service import gemini_service
from app.ai.roboflow_service import roboflow_service
from app.services.roboflow.inference_service import roboflow_central_engine
from app.services.roboflow.model_registry import model_registry
from app.services.location.ocr_service import ocr_location_service
from app.services.location.landmark_service import landmark_service

# Ensure workers package is discoverable for local fallback models
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from workers.adapters.road_damage.adapter import road_damage_adapter
from workers.adapters.water_leak.adapter import water_leak_adapter

class AIOrchestrator:
    """
    Centralized AI Orchestrator for GramaSeva (Part 5).
    Coordinates:
    - Input Image Validation & Integrity
    - Roboflow 5-Model Suite with Specialist Routing
    - Local Fallback Specialist Adapters
    - Gemini Multimodal Visual Understanding & Description Generation
    - Photo Location Clues (OCR Signboards & Verified Landmark Candidates)
    - Separate Duplicate Detection Engine (Spatial + Category + Visual)
    - ModelRun Audit Trail Persistence
    """

    def __init__(self):
        self.roboflow_engine = roboflow_central_engine
        self.gemini = gemini_service
        self.ocr = ocr_location_service
        self.landmarks = landmark_service

    def orchestrate_complaint_analysis(
        self,
        image_bytes: bytes,
        filename: str = "upload.jpg",
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        village_name: Optional[str] = None,
        category_hint: Optional[str] = None,
        citizen_notes: Optional[str] = None,
        full_evaluation: bool = False,
        locale: str = "en",
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        start_time = time.perf_counter()

        # 1. Validate image
        valid, err_msg, pil_img = roboflow_service.validate_image_bytes(image_bytes)
        if not valid or pil_img is None:
            return {
                "status": "error",
                "error": err_msg or "Invalid image file format or size.",
                "latency_ms": int((time.perf_counter() - start_time) * 1000)
            }

        # 2. Call Roboflow Central 5-Model Engine
        rf_analysis = self.roboflow_engine.analyze(
            image_bytes=image_bytes,
            filename=filename,
            category_hint=category_hint,
            full_evaluation=full_evaluation,
        )

        # 3. Call OCR and Landmark Location Clues
        ocr_res = self.ocr.extract_location_clues(pil_img)
        landmark_res = self.landmarks.find_candidate_landmarks(pil_img, latitude, longitude)

        photo_location_status = "NO_PHOTO_CLUES"
        photo_location_summary = "No village signage or landmarks detected in photograph."
        if ocr_res.get("has_location_clues"):
            photo_location_status = "PHOTO_CLUES_FOUND"
            villages_found = ", ".join(ocr_res.get("matched_villages", []))
            photo_location_summary = f"Signboard text extracted: {villages_found}"
        elif landmark_res.get("has_candidate_landmarks"):
            photo_location_status = "PHOTO_CLUES_FOUND"
            top_lm = landmark_res["candidates"][0]
            photo_location_summary = f"Landmark identified: {top_lm['name']} ({int(top_lm['similarity_score'] * 100)}% match)"

        # 4. Extract detections and model summaries
        raw_detections = rf_analysis.get("detections", [])
        observations: List[Dict[str, Any]] = []
        for idx, d in enumerate(raw_detections):
            raw_box = d.get("box_pixels") or [0, 0, 100, 100]
            observations.append({
                "class_id": idx,
                "label": f"[{d.get('model_source', 'AI')}] {d.get('class', 'defect')}",
                "confidence": round(float(d.get("confidence", 0.5)), 3),
                "bbox": [raw_box[0], raw_box[1], raw_box[2], raw_box[3]],
            })

        predicted_category = rf_analysis.get("predicted_category") or category_hint or "road_damage"
        confidence_score = rf_analysis.get("confidence_score")
        defect_label = rf_analysis.get("defect_label")
        issue_title = rf_analysis.get("issue_title") or "Civic Defect"
        ai_description = rf_analysis.get("ai_description") or ""
        annotated_b64 = rf_analysis.get("annotated_image_base64")
        model_provider = "roboflow-5-model-suite"
        model_id = "roboflow-central-engine"
        comparison = rf_analysis.get("comparison") or {}
        consensus_status = rf_analysis.get("consensus_status") or "EVALUATED"

        model_summaries = []
        for m in rf_analysis.get("individual_models", []):
            model_summaries.append({
                "model_key": m.get("model_key", ""),
                "model_name": m.get("model_name", ""),
                "model_id": m.get("model_id", ""),
                "status": m.get("status", "COMPLETED"),
                "primary_category": m.get("dominant_category"),
                "defect_label": None,
                "confidence_score": m.get("max_confidence"),
                "detections_count": m.get("raw_detections_count", 0),
                "latency_ms": m.get("latency_ms", 0),
                "error": m.get("error"),
            })

        # 5. Local specialist fallback if Roboflow returns 0 detections and is offline/unauthorized
        if not observations and all(m.get("status") in ("UNAUTHORIZED", "ERROR", "TIMEOUT") for m in rf_analysis.get("individual_models", [])):
            rdd_res = road_damage_adapter.predict(image_bytes)
            if rdd_res.get("observations") and len(rdd_res["observations"]) > 0:
                raw_obs = rdd_res["observations"]
                observations = [
                    {
                        "class_id": o.get("class_id", 0),
                        "label": o.get("label", "Road Defect"),
                        "confidence": round(float(o.get("confidence", 0.5)), 3),
                        "bbox": o.get("bbox", []),
                    }
                    for o in raw_obs
                ]
                predicted_category = "road_damage"
                confidence_score = round(float(rdd_res.get("confidence_score") or observations[0]["confidence"]), 3)
                defect_label = observations[0]["label"]
                issue_title = f"{defect_label} on Village Road"
                model_id = rdd_res.get("model_id", "oracl4-rdd-yolov8s")
                model_provider = "roboflow-local-fallback"
                ai_description = f"{defect_label} road damage observed in captured evidence at {village_name or 'reported location'}."
                consensus_status = "LOCAL_FALLBACK"
            else:
                leak_res = water_leak_adapter.predict(image_bytes)
                if leak_res.get("observations") and len(leak_res["observations"]) > 0:
                    raw_obs = leak_res["observations"]
                    observations = [
                        {
                            "class_id": o.get("class_id", 0),
                            "label": o.get("label", "Water Leak"),
                            "confidence": round(float(o.get("confidence", 0.5)), 3),
                            "bbox": o.get("bbox", []),
                        }
                        for o in raw_obs
                    ]
                    predicted_category = "water_leak"
                    confidence_score = round(float(leak_res.get("confidence_score") or observations[0]["confidence"]), 3)
                    defect_label = observations[0]["label"]
                    issue_title = f"{defect_label.capitalize()} in Water Pipeline"
                    model_id = leak_res.get("model_id", "msunusi-pipeline-leak-yolo")
                    model_provider = "roboflow-local-fallback"
                    ai_description = f"{defect_label.capitalize()} pipeline issue observed in captured evidence at {village_name or 'reported location'}."
                    consensus_status = "LOCAL_FALLBACK"

        # 6. Gemini Multimodal & Natural Language Enrichment
        gemini_details = self.gemini.generate_complaint_details(
            category=predicted_category,
            defect_label=defect_label,
            village_name=village_name,
            citizen_notes=citizen_notes,
            locale=locale,
        )
        if gemini_details.get("description"):
            ai_description = gemini_details["description"]
        if gemini_details.get("title") and issue_title in ("Civic Defect", "Civic Issue"):
            issue_title = gemini_details["title"]

        # 7. Render bounding box annotation if not already provided
        if annotated_b64 is None and observations:
            try:
                draw_img = pil_img.copy()
                draw = ImageDraw.Draw(draw_img)
                w, h = draw_img.size
                for obs in observations:
                    bbox = obs["bbox"]
                    if len(bbox) >= 4:
                        y1, x1, y2, x2 = bbox
                        if x1 <= 1.0 and y1 <= 1.0 and x2 <= 1.0 and y2 <= 1.0:
                            x1 *= w
                            y1 *= h
                            x2 *= w
                            y2 *= h
                        x1, y1, x2, y2 = max(0, x1), max(0, y1), min(w, x2), min(h, y2)
                        draw.rectangle([x1, y1, x2, y2], outline="#EF4444", width=4)
                        lbl_text = f"{obs['label']} {int(obs['confidence'] * 100)}%"
                        pill_w = len(lbl_text) * 8 + 14
                        pill_h = 22
                        pill_y = max(0, y1 - pill_h - 4) if y1 > pill_h + 4 else y1 + 4
                        draw.rectangle([x1, pill_y, x1 + pill_w, pill_y + pill_h], fill="#EF4444")
                        draw.text((x1 + 6, pill_y + 3), lbl_text, fill="#FFFFFF")

                out_buf = io.BytesIO()
                draw_img.save(out_buf, format="JPEG", quality=88)
                annotated_b64 = "data:image/jpeg;base64," + base64.b64encode(out_buf.getvalue()).decode("utf-8")
            except Exception as e:
                pass

        # 8. Separate Duplicate Detection Engine
        duplicate_detected = False
        duplicate_message = None
        duplicate_issue_id = None
        duplicate_tracking_id = None
        duplicate_distance_meters = None

        if latitude is not None and longitude is not None and db is not None:
            try:
                candidates = (
                    db.query(Issue)
                    .filter(
                        Issue.latitude.isnot(None),
                        Issue.longitude.isnot(None),
                        Issue.status.notin_(["REJECTED", "RESOLVED"])
                    )
                    .all()
                )
                for cand in candidates:
                    d_lat = (cand.latitude - latitude) * 111320
                    d_lon = (cand.longitude - longitude) * 111320 * math.cos(math.radians(latitude))
                    dist = math.sqrt(d_lat**2 + d_lon**2)
                    if dist <= 120 and (cand.category == predicted_category or dist <= 40):
                        duplicate_detected = True
                        duplicate_issue_id = cand.id
                        duplicate_tracking_id = cand.reference_number
                        duplicate_distance_meters = round(dist, 1)
                        duplicate_message = (
                            f"This issue may have already been reported at this location ({round(dist)}m away, Ref: {cand.reference_number}). "
                            f"Please review the existing report before submitting another complaint."
                        )
                        break
            except Exception as e:
                pass

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        # 9. Persist ModelRun audit records if database session provided
        if db is not None:
            try:
                raw_results = rf_analysis.get("individual_models", [])
                for m in raw_results:
                    m_run = ModelRun(
                        id=str(uuid.uuid4()),
                        model_id=m.get("model_id", "roboflow-model"),
                        model_provider="roboflow",
                        model_revision="v1.0.0",
                        task="object_detection",
                        status=m.get("status", "COMPLETED"),
                        category_suggestion=m.get("dominant_category"),
                        confidence_score=m.get("max_confidence"),
                        detections_json=json.dumps(m.get("detections", [])),
                        latency_ms=m.get("latency_ms", 0),
                        requires_human_review=True,
                        error_info=m.get("error"),
                    )
                    db.add(m_run)

                run_rec = ModelRun(
                    id=str(uuid.uuid4()),
                    model_id=model_id,
                    model_provider=model_provider,
                    model_revision="v1.0.0",
                    task="object_detection",
                    status=consensus_status,
                    category_suggestion=predicted_category,
                    confidence_score=confidence_score,
                    detections_json=json.dumps(observations),
                    latency_ms=latency_ms,
                    requires_human_review=True,
                    error_info=None,
                    duplicate_candidates_json=json.dumps({
                        "detected": duplicate_detected,
                        "tracking_id": duplicate_tracking_id,
                        "distance": duplicate_distance_meters,
                    }) if duplicate_detected else None,
                )
                db.add(run_rec)
                db.commit()
            except Exception as e:
                pass

        return {
            "status": "completed",
            "issue_title": issue_title,
            "predicted_category": predicted_category,
            "defect_label": defect_label,
            "confidence_score": confidence_score,
            "ai_description": ai_description,
            "observations": observations,
            "requires_human_review": True,
            "model_id": model_id,
            "model_provider": model_provider,
            "latency_ms": latency_ms,
            "annotated_image_base64": annotated_b64,
            "model_summaries": model_summaries,
            "comparison": comparison,
            "ai_consensus_status": consensus_status,
            "duplicate_detected": duplicate_detected,
            "duplicate_message": duplicate_message,
            "duplicate_issue_id": duplicate_issue_id,
            "duplicate_tracking_id": duplicate_tracking_id,
            "duplicate_distance_meters": duplicate_distance_meters,
            "ocr_location_clues": ocr_res,
            "landmark_candidates": landmark_res.get("candidates"),
            "photo_location_status": photo_location_status,
            "photo_location_summary": photo_location_summary,
        }

ai_orchestrator = AIOrchestrator()
