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
    return [
        ModelHealthItem(
            model_id=rdd_health["model_id"],
            version=rdd_health["version"],
            task=rdd_health["task"],
            ready=rdd_health["ready"],
            checkpoint_sha256=rdd_health["checkpoint_sha256"],
            classes=rdd_health["classes"],
            error=rdd_health["error"],
        )
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
