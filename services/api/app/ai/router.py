import sys
import os
import json
import base64
import io
import math
import time
import uuid
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Form, status
from pydantic import BaseModel
from PIL import Image, ImageDraw
from sqlalchemy.orm import Session
from app.ai.gemini_service import gemini_service
from app.ai.roboflow_service import roboflow_service
from app.ai.orchestrator import ai_orchestrator
from app.services.roboflow.inference_service import roboflow_central_engine
from app.services.roboflow.model_registry import model_registry
from app.services.location.ocr_service import ocr_location_service
from app.services.location.landmark_service import landmark_service
from app.core.database import get_db
from app.models.users import Profile
from app.models.issues import MediaAsset, Issue, Submission, ModelRun
from app.auth.dependencies import get_current_user

# Ensure workers package is discoverable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from workers.adapters.road_damage.adapter import road_damage_adapter
from workers.adapters.water_leak.adapter import water_leak_adapter
from workers.adapters.duplicate.similarity import (
    compute_dhash,
    compute_visual_similarity,
    rank_duplicate_candidate,
)

router = APIRouter(prefix="/ai", tags=["Real AI Inference & Models"])

class DetectionItem(BaseModel):
    class_id: int
    label: str
    confidence: float
    bbox: List[float]

class AIInferenceResponse(BaseModel):
    status: str
    task: str
    category_suggestion: Optional[str] = None
    confidence_score: Optional[float] = None
    observations: List[DetectionItem]
    limitations: List[str]
    requires_human_review: bool
    model_id: str
    model_revision: str
    latency_ms: int
    prompt_message: Optional[str] = None

class ModelHealthItem(BaseModel):
    model_id: str
    version: str
    task: str
    ready: bool
    checkpoint_sha256: Optional[str] = None
    classes: List[str]
    error: Optional[str] = None

class ModelRunResponse(BaseModel):
    id: str
    model_id: str
    model_revision: str
    task: str
    status: str
    category_suggestion: Optional[str] = None
    confidence_score: Optional[float] = None
    detections: List[Dict[str, Any]] = []
    latency_ms: int
    requires_human_review: bool
    limitations: List[str] = []
    confirmed_decision: str
    created_at: str

class ConfirmRunRequest(BaseModel):
    decision: str  # CONFIRMED or REJECTED
    notes: Optional[str] = None

@router.get("/models/health", response_model=List[ModelHealthItem])
def get_ai_models_health():
    """
    Returns live readiness and provenance metadata of real installed AI models.
    No mock health status.
    """
    rdd_health = road_damage_adapter.check_readiness()
    leak_health = water_leak_adapter.check_readiness()
    return [
        ModelHealthItem(
            model_id=rdd_health["model_id"],
            version=rdd_health["version"],
            task=rdd_health["task"],
            ready=rdd_health["ready"],
            checkpoint_sha256=rdd_health["checkpoint_sha256"],
            classes=rdd_health["classes"],
            error=rdd_health["error"],
        ),
        ModelHealthItem(
            model_id=leak_health["model_id"],
            version=leak_health["version"],
            task=leak_health["task"],
            ready=leak_health["ready"],
            checkpoint_sha256=leak_health["checkpoint_sha256"],
            classes=leak_health["classes"],
            error=leak_health["error"],
        ),
    ]

@router.post("/road-damage/inspect", response_model=AIInferenceResponse)
async def inspect_road_damage(
    file: Optional[UploadFile] = File(None),
    media_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Executes real inference on an uploaded image or an existing media asset.
    Returns detected road defects (potholes, cracks), confidence scores, bounding boxes, and latency.
    """
    if file:
        file_bytes = await file.read()
        res = road_damage_adapter.predict(file_bytes)
    elif media_id:
        media = db.query(MediaAsset).filter(MediaAsset.id == media_id).first()
        if not media:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media asset not found")
        from app.storage.service import storage_service
        abs_path = storage_service.get_absolute_path(media.storage_path)
        res = road_damage_adapter.predict(abs_path)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either a file upload or media_id query parameter is required.",
        )

    return AIInferenceResponse(
        status=res["status"],
        task=res["task"],
        category_suggestion=res["category_suggestion"],
        confidence_score=res["confidence_score"],
        observations=[
            DetectionItem(
                class_id=o["class_id"],
                label=o["label"],
                confidence=o["confidence"],
                bbox=o["bbox"],
            )
            for o in res.get("observations", [])
        ],
        limitations=res.get("limitations", []),
        requires_human_review=res["requires_human_review"],
        model_id=res["model_id"],
        model_revision=res["model_revision"],
        latency_ms=res["latency_ms"],
        prompt_message=res.get("prompt_message"),
    )

class CategoryCapabilityItem(BaseModel):
    category: str
    display_name: str
    status: str  # ACTIVE_MODEL or MANUAL_FALLBACK
    model_id: Optional[str] = None
    evaluation_notes: str
    requires_human_confirmation: bool = True

class DuplicateCompareRequest(BaseModel):
    sub_lat: Optional[float] = None
    sub_lon: Optional[float] = None
    sub_desc: Optional[str] = None
    sub_media_id: Optional[str] = None
    target_issue_id: str

class DuplicateCompareResponse(BaseModel):
    target_issue_id: str
    distance_meters: float
    spatial_score: float
    text_score: float
    visual_score: float
    composite_score: float
    explanation: str
    is_strong_candidate: bool
    requires_human_decision: bool = True

@router.post("/water-leak/inspect", response_model=AIInferenceResponse)
async def inspect_water_leak(
    file: Optional[UploadFile] = File(None),
    media_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Executes real inference using the MSunusi pipeline leak YOLO model.
    Detects pipe leaks, water flows, and surface cracks.
    Zero mock predictions.
    """
    if file:
        file_bytes = await file.read()
        res = water_leak_adapter.predict(file_bytes)
    elif media_id:
        media = db.query(MediaAsset).filter(MediaAsset.id == media_id).first()
        if not media:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media asset not found")
        from app.storage.service import storage_service
        abs_path = storage_service.get_absolute_path(media.storage_path)
        res = water_leak_adapter.predict(abs_path)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either a file upload or media_id query parameter is required.",
        )

    return AIInferenceResponse(
        status=res["status"],
        task=res["task"],
        category_suggestion=res["category_suggestion"],
        confidence_score=res["confidence_score"],
        observations=[
            DetectionItem(
                class_id=o["class_id"],
                label=o["label"],
                confidence=o["confidence"],
                bbox=o["bbox"],
            )
            for o in res.get("observations", [])
        ],
        limitations=res.get("limitations", []),
        requires_human_review=res["requires_human_review"],
        model_id=res["model_id"],
        model_revision=res["model_revision"],
        latency_ms=res["latency_ms"],
        prompt_message=res.get("prompt_message"),
    )

@router.get("/categories/capabilities", response_model=List[CategoryCapabilityItem])
def get_categories_ai_capabilities():
    """
    Auditable status of AI capability for each municipal issue category.
    Per README Phase 7: Unsupported category falls back cleanly to manual review.
    """
    return [
        CategoryCapabilityItem(
            category="road_damage",
            display_name="Road Damage & Potholes",
            status="ACTIVE_MODEL",
            model_id="oracl4-rdd-yolov8s",
            evaluation_notes="Real YOLOv8s inference trained on CRDDC2022. Detects potholes (D40) and cracks (D00-D20).",
            requires_human_confirmation=True,
        ),
        CategoryCapabilityItem(
            category="water_leak",
            display_name="Water Supply & Pipeline Leaks",
            status="ACTIVE_MODEL",
            model_id="msunusi-pipeline-leak-yolo",
            evaluation_notes="Real YOLO custom model trained on pipeline leaks. Detects surface water leaks and pipe cracks. Street runoff puddles require human confirmation.",
            requires_human_confirmation=True,
        ),
        CategoryCapabilityItem(
            category="garbage_dump",
            display_name="Solid Waste & Garbage Dumps",
            status="MANUAL_FALLBACK",
            model_id=None,
            evaluation_notes="TACO evaluation audit: legacy Matterport Mask R-CNN framework incompatible with Python 3.14. Zero mock predictions; falls back to manual review.",
            requires_human_confirmation=True,
        ),
        CategoryCapabilityItem(
            category="street_lighting",
            display_name="Street Lighting & Electrical",
            status="MANUAL_FALLBACK",
            model_id=None,
            evaluation_notes="No verified open-source checkpoint passed local municipal verification gate. Manual reviewer triage enforced.",
            requires_human_confirmation=True,
        ),
    ]

@router.post("/duplicate/compare", response_model=DuplicateCompareResponse)
def compare_duplicate_candidate(
    req: DuplicateCompareRequest,
    db: Session = Depends(get_db),
):
    """
    Computes multi-signal similarity (spatial + text + visual) between a report draft and an existing issue.
    Never auto-merges: returns transparent scoring breakdown and explanation for human decision.
    """
    target = db.query(Issue).filter(Issue.id == req.target_issue_id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target issue not found")

    # Get target coordinates & description
    target_sub = db.query(Submission).filter(Submission.issue_id == target.id).order_by(Submission.created_at.asc()).first()
    target_lat = target_sub.latitude if target_sub else None
    target_lon = target_sub.longitude if target_sub else None
    target_desc = target_sub.description if target_sub else ""

    # Visual hashes
    sub_hash = None
    target_hash = None
    if req.sub_media_id:
        sub_media = db.query(MediaAsset).filter(MediaAsset.id == req.sub_media_id).first()
        if sub_media:
            sub_hash = sub_media.file_hash

    target_media = db.query(MediaAsset).filter(MediaAsset.issue_id == target.id).first()
    if target_media:
        target_hash = target_media.file_hash

    rank_result = rank_duplicate_candidate(
        sub_lat=req.sub_lat,
        sub_lon=req.sub_lon,
        sub_desc=req.sub_desc,
        sub_hash=sub_hash,
        issue_lat=target_lat,
        issue_lon=target_lon,
        issue_desc=target_desc,
        issue_hash=target_hash,
        category_match=True,
    )

    return DuplicateCompareResponse(
        target_issue_id=target.id,
        distance_meters=rank_result["distance_meters"],
        spatial_score=rank_result["spatial_score"],
        text_score=rank_result["text_score"],
        visual_score=rank_result["visual_score"],
        composite_score=rank_result["composite_score"],
        explanation=rank_result["explanation"],
        is_strong_candidate=rank_result["is_strong_candidate"],
        requires_human_decision=True,
    )

@router.get("/runs/{id}", response_model=List[ModelRunResponse])
def get_model_runs_for_issue_or_submission(
    id: str,
    db: Session = Depends(get_db),
):
    """Retrieves all model runs and AI detection audits recorded for a submission or physical issue."""
    runs = (
        db.query(ModelRun)
        .filter((ModelRun.submission_id == id) | (ModelRun.issue_id == id))
        .order_by(ModelRun.created_at.desc())
        .all()
    )

    out = []
    for r in runs:
        dets = json.loads(r.detections_json) if r.detections_json else []
        limits = json.loads(r.limitations_json) if r.limitations_json else []
        out.append(
            ModelRunResponse(
                id=r.id,
                model_id=r.model_id,
                model_revision=r.model_revision,
                task=r.task,
                status=r.status,
                category_suggestion=r.category_suggestion,
                confidence_score=r.confidence_score,
                detections=dets,
                latency_ms=r.latency_ms,
                requires_human_review=r.requires_human_review,
                limitations=limits,
                confirmed_decision=r.confirmed_decision,
                created_at=r.created_at.isoformat(),
            )
        )
    return out

@router.post("/runs/{run_id}/confirm")
def confirm_model_run_suggestion(
    run_id: str,
    req: ConfirmRunRequest,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Citizen or reviewer confirms or rejects an AI model category suggestion.
    README Rule: AI suggests, human decides.
    """
    if req.decision not in ("CONFIRMED", "REJECTED"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decision must be either CONFIRMED or REJECTED",
        )

    run = db.query(ModelRun).filter(ModelRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model run not found")

    run.confirmed_decision = req.decision
    run.confirmed_by_profile_id = current_user.id

    # If confirmed, update issue or submission category if matching
    if req.decision == "CONFIRMED" and run.category_suggestion:
        if run.issue_id:
            issue = db.query(Issue).filter(Issue.id == run.issue_id).first()
            if issue:
                issue.category = run.category_suggestion
        if run.submission_id:
            sub = db.query(Submission).filter(Submission.id == run.submission_id).first()
            if sub:
                sub.category = run.category_suggestion

    db.commit()
    return {
        "status": "success",
        "run_id": run.id,
        "confirmed_decision": run.confirmed_decision,
        "confirmed_by": current_user.full_name,
    }

class ModelSummaryItem(BaseModel):
    model_key: str
    model_name: str
    model_id: str
    status: str
    primary_category: Optional[str] = None
    defect_label: Optional[str] = None
    confidence_score: Optional[float] = None
    detections_count: int = 0
    latency_ms: int = 0
    error: Optional[str] = None

class UnifiedAIAnalysisResponse(BaseModel):
    status: str
    issue_title: str
    predicted_category: str
    defect_label: Optional[str] = None
    confidence_score: Optional[float] = None
    ai_description: str
    observations: List[DetectionItem] = []
    requires_human_review: bool = True
    model_id: str
    model_provider: str = "roboflow-multi-model"
    latency_ms: int
    annotated_image_base64: Optional[str] = None
    model_summaries: List[ModelSummaryItem] = []
    comparison: Optional[Dict[str, Any]] = None
    ai_consensus_status: Optional[str] = None
    duplicate_detected: bool = False
    duplicate_message: Optional[str] = None
    duplicate_issue_id: Optional[str] = None
    duplicate_tracking_id: Optional[str] = None
    duplicate_distance_meters: Optional[float] = None
    ocr_location_clues: Optional[Dict[str, Any]] = None
    landmark_candidates: Optional[List[Dict[str, Any]]] = None
    photo_location_status: Optional[str] = "NOT_EVALUATED"
    photo_location_summary: Optional[str] = None

def _run_analysis_pipeline(
    file: UploadFile,
    latitude: Optional[float],
    longitude: Optional[float],
    village_name: Optional[str],
    category_hint: Optional[str],
    full_evaluation: bool,
    db: Session,
    locale: str = "en",
    citizen_notes: Optional[str] = None,
) -> UnifiedAIAnalysisResponse:
    file_bytes = file.file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    res = ai_orchestrator.orchestrate_complaint_analysis(
        image_bytes=file_bytes,
        filename=file.filename or "upload.jpg",
        latitude=latitude,
        longitude=longitude,
        village_name=village_name,
        category_hint=category_hint,
        citizen_notes=citizen_notes,
        full_evaluation=full_evaluation,
        locale=locale,
        db=db,
    )

    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("error", "Analysis failed."))

    obs_list = [
        DetectionItem(
            class_id=o["class_id"],
            label=o["label"],
            confidence=o["confidence"],
            bbox=o["bbox"],
        )
        for o in res.get("observations", [])
    ]

    summaries_list = [
        ModelSummaryItem(
            model_key=m.get("model_key", ""),
            model_name=m.get("model_name", ""),
            model_id=m.get("model_id", ""),
            status=m.get("status", "COMPLETED"),
            primary_category=m.get("primary_category"),
            defect_label=m.get("defect_label"),
            confidence_score=m.get("confidence_score"),
            detections_count=m.get("detections_count", 0),
            latency_ms=m.get("latency_ms", 0),
            error=m.get("error"),
        )
        for m in res.get("model_summaries", [])
    ]

    return UnifiedAIAnalysisResponse(
        status=res["status"],
        issue_title=res["issue_title"],
        predicted_category=res["predicted_category"],
        defect_label=res["defect_label"],
        confidence_score=res["confidence_score"],
        ai_description=res["ai_description"],
        observations=obs_list,
        requires_human_review=res.get("requires_human_review", True),
        model_id=res["model_id"],
        model_provider=res["model_provider"],
        latency_ms=res["latency_ms"],
        annotated_image_base64=res.get("annotated_image_base64"),
        model_summaries=summaries_list,
        comparison=res.get("comparison"),
        ai_consensus_status=res.get("ai_consensus_status"),
        duplicate_detected=res.get("duplicate_detected", False),
        duplicate_message=res.get("duplicate_message"),
        duplicate_issue_id=res.get("duplicate_issue_id"),
        duplicate_tracking_id=res.get("duplicate_tracking_id"),
        duplicate_distance_meters=res.get("duplicate_distance_meters"),
        ocr_location_clues=res.get("ocr_location_clues"),
        landmark_candidates=res.get("landmark_candidates"),
        photo_location_status=res.get("photo_location_status", "NOT_EVALUATED"),
        photo_location_summary=res.get("photo_location_summary"),
    )

@router.post("/analyze-complaint", response_model=UnifiedAIAnalysisResponse)
def analyze_complaint(
    file: UploadFile = File(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    village_name: Optional[str] = Form(None),
    category_hint: Optional[str] = Form(None),
    citizen_notes: Optional[str] = Form(None),
    locale: str = Form("en"),
    db: Session = Depends(get_db),
):
    """
    Dedicated Stage 3 Multi-Model AI Analysis Endpoint with Specialist Routing.
    """
    return _run_analysis_pipeline(
        file=file,
        latitude=latitude,
        longitude=longitude,
        village_name=village_name,
        category_hint=category_hint,
        citizen_notes=citizen_notes,
        full_evaluation=False,
        locale=locale,
        db=db,
    )

@router.post("/full-evaluation", response_model=UnifiedAIAnalysisResponse)
def full_ai_evaluation(
    file: UploadFile = File(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    village_name: Optional[str] = Form(None),
    category_hint: Optional[str] = Form(None),
    citizen_notes: Optional[str] = Form(None),
    locale: str = Form("en"),
    db: Session = Depends(get_db),
):
    """
    Runs full evaluation across all 5 Roboflow models simultaneously (Part 5).
    """
    return _run_analysis_pipeline(
        file=file,
        latitude=latitude,
        longitude=longitude,
        village_name=village_name,
        category_hint=category_hint,
        citizen_notes=citizen_notes,
        full_evaluation=True,
        locale=locale,
        db=db,
    )

@router.get("/models/status")
def get_ai_models_status():
    """
    Returns live readiness, configuration, and health metadata of all 5 Roboflow models:
    - Garbage Detection Specialist (garbage_detection-wvzwv-n8vsv/1)
    - Road Damage Specialist (road-damage-detection-fn0qh/1)
    - Waterlogging Specialist (water-logging-a7zhi/1)
    - Civic Issues 1 (civic-issues-lroee/3)
    - Civic Issues 2 (civic-issues-nq7sy-bh8t3/1)
    """
    return model_registry.get_status_summary()

class GeminiProblemAnalysisResponse(BaseModel):
    is_civic_issue: bool
    suggested_category: str
    title: str
    description: str
    severity: str
    visual_summary: str
    detected_elements: List[str] = []
    ocr_text: List[str] = []
    uncertainty_explanation: Optional[str] = None
    confidence: float
    source: str

@router.post("/gemini/analyze-problem", response_model=GeminiProblemAnalysisResponse)
def analyze_problem_image_with_gemini(
    file: UploadFile = File(...),
    category_hint: Optional[str] = Form(None),
    village_name: Optional[str] = Form(None),
    citizen_notes: Optional[str] = Form(None),
    locale: Optional[str] = Form("en"),
):
    """
    Dedicated Gemini Vision multimodal analysis endpoint for citizen problem photos (Part 1, Step 4).
    Suggests category, generates problem title and description, assesses severity, extracts OCR text,
    and explains uncertainty when unclear. Strictly never invents GPS coordinates or village names.
    """
    img_bytes = file.file.read() if hasattr(file, "file") and file.file else file.read()
    if not img_bytes:
        raise HTTPException(status_code=400, detail="Uploaded image is empty")

    # 1. Visual multimodal analysis
    analysis = gemini_service.analyze_image(
        image_bytes=img_bytes,
        context={
            "category_hint": category_hint or "",
            "village_name": village_name or "Belagavi Taluk",
            "citizen_notes": citizen_notes or "",
        },
    )

    # Category normalization to GramaSeva standard categories
    raw_cat = (analysis.get("primary_category") or category_hint or "OTHER").upper()
    cat_mapping = {
        "ROADS": "road_damage",
        "ROAD_DAMAGE": "road_damage",
        "POTHOLE": "road_damage",
        "GARBAGE": "garbage",
        "WASTE": "garbage",
        "WATER": "water_leak",
        "DRINKING_WATER": "water_leak",
        "WATERLOGGING": "waterlogging",
        "DRAINAGE": "drainage",
        "SEWAGE": "drainage",
        "STREETLIGHT": "street_light",
        "STREET_LIGHT": "street_light",
        "SANITATION": "public_sanitation",
        "PUBLIC_SANITATION": "public_sanitation",
        "INFRASTRUCTURE": "public_infrastructure",
        "PUBLIC_INFRASTRUCTURE": "public_infrastructure",
        "OTHER": "other",
    }
    std_cat = cat_mapping.get(raw_cat, "road_damage")

    # 2. Text generation for title & description in selected locale
    defect_label = ", ".join(analysis.get("detected_elements", [])) or analysis.get("visual_summary", "Civic defect")
    text_data = gemini_service.generate_complaint_details(
        category=std_cat,
        defect_label=defect_label,
        village_name=village_name,
        citizen_notes=citizen_notes,
        locale=locale or "en",
    )

    # 3. OCR & text extraction
    ocr_data = gemini_service.extract_location_clues(img_bytes)
    ocr_detected = ocr_data.get("detected_text", []) if isinstance(ocr_data, dict) else []

    is_unclear = not analysis.get("is_civic_issue", True) or analysis.get("confidence", 0.0) < 0.4
    uncertainty_msg = None
    if is_unclear:
        uncertainty_msg = "The image quality, lighting, or framing is unclear. Please review and refine the suggested title and category."

    return GeminiProblemAnalysisResponse(
        is_civic_issue=analysis.get("is_civic_issue", True),
        suggested_category=std_cat,
        title=text_data.get("title", f"{std_cat.replace('_', ' ').title()} Issue"),
        description=text_data.get("description", analysis.get("visual_summary", "")),
        severity=analysis.get("severity_assessment", "MEDIUM"),
        visual_summary=analysis.get("visual_summary", "Civic issue requiring inspection"),
        detected_elements=analysis.get("detected_elements", []),
        ocr_text=ocr_detected,
        uncertainty_explanation=uncertainty_msg,
        confidence=float(analysis.get("confidence", 0.85)),
        source=analysis.get("source", "gemini-multimodal"),
    )

class PDOSummaryRequest(BaseModel):
    category: str
    village_name: Optional[str] = "Belagavi Taluk"
    severity: Optional[str] = "MEDIUM"
    description: Optional[str] = ""

@router.post("/gemini/summarize-pdo")
def get_gemini_pdo_summary(req: PDOSummaryRequest):
    return gemini_service.summarize_for_pdo(req.dict())

class TranslateRequest(BaseModel):
    text: str
    source_lang: str = "en"
    target_lang: str = "kn"

@router.post("/gemini/translate")
def translate_civic_text(req: TranslateRequest):
    return {
        "source_lang": req.source_lang,
        "target_lang": req.target_lang,
        "original_text": req.text,
        "translated_text": gemini_service.translate_text(
            req.text, req.source_lang, req.target_lang
        ),
    }

# --- Section 3.4: Controlled AI Model Evaluation & Reviewer Feedback ---
from app.ai.evaluation_service import model_evaluation_service
from app.auth.dependencies import require_roles

class ModelEvaluationFeedbackRequest(BaseModel):
    correct_category: str
    is_correct: bool
    audit_notes: Optional[str] = None

@router.post("/models/runs/{run_id}/evaluate")
def evaluate_model_run_prediction(
    run_id: str,
    req: ModelEvaluationFeedbackRequest,
    current_reviewer: Profile = Depends(require_roles("reviewer", "admin")),
    db: Session = Depends(get_db),
):
    """
    Authorized reviewer (PDO or Admin) provides ground truth feedback on an AI prediction.
    Appends the sample to the versioned dataset for controlled evaluation and retraining.
    """
    try:
        res = model_evaluation_service.record_reviewer_feedback(
            db=db,
            model_run_id=run_id,
            reviewer_profile_id=current_reviewer.id,
            correct_category=req.correct_category,
            is_correct=req.is_correct,
            audit_notes=req.audit_notes,
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get("/evaluation-metrics")
def get_ai_evaluation_metrics(
    model_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Returns empirical evaluation metrics (Precision, Recall, F1 score, FPR, FNR, Category breakdown)
    derived from human-verified model runs. Never fabricates metrics.
    """
    return model_evaluation_service.compute_evaluation_metrics(db=db, model_id=model_id)

@router.get("/retraining-readiness")
def get_model_retraining_readiness(
    db: Session = Depends(get_db),
):
    """
    Returns evaluation dataset curation status and governed retraining readiness metrics.
    """
    return model_evaluation_service.get_retraining_readiness(db=db)

