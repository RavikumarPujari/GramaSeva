import sys
import os
import json
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
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
