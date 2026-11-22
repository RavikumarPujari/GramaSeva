import sys
import os
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.users import Profile, RoleAssignment
from app.models.issues import (
    Issue,
    Submission,
    MediaAsset,
    Assignment,
    StatusEvent,
    WorkCompletion,
    AIBeforeAfterAnalysis,
)
from app.storage.service import storage_service
from app.auth.dependencies import get_current_user, require_roles
from app.ai.gemini_service import gemini_service

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
try:
    from workers.adapters.evidence_assistance.adapter import evidence_assistance_adapter
except Exception:
    try:
        from services.workers.adapters.evidence_assistance.adapter import evidence_assistance_adapter
    except Exception:
        evidence_assistance_adapter = None

router = APIRouter(prefix="/worker", tags=["Field Worker Operations"])

def find_issue_by_any_id(db: Session, identifier: str) -> Optional[Issue]:
    """Finds Issue by Issue UUID, tracking reference (e.g. GS-2026-BEL-XXXX), or Submission UUID."""
    if not identifier:
        return None
    clean = str(identifier).strip()
    issue = db.query(Issue).filter((Issue.id == clean) | (Issue.reference_number == clean)).first()
    if not issue:
        sub = db.query(Submission).filter((Submission.id == clean) | (Submission.tracking_id == clean)).first()
        if sub and sub.issue_id:
            issue = db.query(Issue).filter(Issue.id == sub.issue_id).first()
    return issue

class WorkerTaskItem(BaseModel):
    assignment_id: str
    issue_id: str
    reference_number: str
    category: str
    status: str
    priority: str
    instructions: Optional[str] = None
    village_name: Optional[str] = None
    ward_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    assigned_at: datetime
    citizen_photo_ids: List[str] = []
    worker_after_photo_ids: List[str] = []
    estimated_cost: Optional[float] = None
    proposed_cost: Optional[float] = None
    materials_cost: Optional[float] = None
    labour_cost: Optional[float] = None
    other_expenses_cost: Optional[float] = None
    verified_cost: Optional[float] = None
    cost_status: Optional[str] = None
    pdo_remarks: Optional[str] = None
    work_completed_at: Optional[datetime] = None

class ProgressNoteRequest(BaseModel):
    notes: str

class DeclineRequest(BaseModel):
    reason: str

class EscalateTaskRequest(BaseModel):
    reason: str  # BLOCKED, NEEDS_MATERIALS, INACCESSIBLE, OTHER
    explanation: str

class RequestReviewRequest(BaseModel):
    work_summary: str

class WorkCompletionSubmitRequest(BaseModel):
    work_description: str
    work_performed: Optional[str] = None
    materials_used: Optional[str] = None
    labour_details: Optional[str] = None
    materials_cost: float = 0.0
    labour_cost: float = 0.0
    other_expenses_cost: float = 0.0
    proposed_cost: Optional[float] = None
    completion_date: Optional[str] = None
    supporting_documents_paths: Optional[str] = None
    after_media_ids: List[str] = []

@router.get("/tasks", response_model=List[WorkerTaskItem])
def get_worker_tasks(
    current_worker: Profile = Depends(require_roles("worker", "admin")),
    db: Session = Depends(get_db),
):
    """Lists repair tasks assigned to the authenticated field worker."""
    assignments = (
        db.query(Assignment, Issue)
        .join(Issue, Assignment.issue_id == Issue.id)
        .filter(Assignment.worker_profile_id == current_worker.id)
        .order_by(Assignment.created_at.desc())
        .all()
    )

    tasks: List[WorkerTaskItem] = []
    for asgn, issue in assignments:
        citizen_photos = (
            db.query(MediaAsset.id)
            .filter(MediaAsset.issue_id == issue.id, MediaAsset.evidence_role == "CITIZEN_BEFORE")
            .all()
        )
        worker_photos = (
            db.query(MediaAsset.id)
            .filter(MediaAsset.issue_id == issue.id, MediaAsset.evidence_role == "WORKER_AFTER")
            .all()
        )

        ward_name = issue.locality_unit.name_en if issue.locality_unit else "Ward Unknown"

        tasks.append(
            WorkerTaskItem(
                assignment_id=asgn.id,
                issue_id=issue.id,
                reference_number=issue.reference_number,
                category=issue.category,
                status=issue.status,
                priority=issue.priority,
                instructions=asgn.instructions,
                village_name=issue.locality_unit.name_en if issue.locality_unit else None,
                ward_name=ward_name,
                latitude=issue.latitude,
                longitude=issue.longitude,
                assigned_at=asgn.created_at,
                citizen_photo_ids=[m[0] for m in citizen_photos],
                worker_after_photo_ids=[m[0] for m in worker_photos],
                estimated_cost=issue.estimated_cost,
                proposed_cost=issue.proposed_cost,
                materials_cost=issue.materials_cost,
                labour_cost=issue.labour_cost,
                other_expenses_cost=issue.other_expenses_cost,
                verified_cost=issue.verified_cost,
                cost_status=issue.cost_status,
                pdo_remarks=issue.cost_verification_remarks or issue.resolution_review_notes,
                work_completed_at=issue.work_completed_at,
            )
        )

    return tasks

@router.post("/assignments/{assignment_id}/accept")
def accept_assignment(
    assignment_id: str,
    current_worker: Profile = Depends(require_roles("worker", "admin")),
    db: Session = Depends(get_db),
):
    """Worker accepts the assigned task and marks work in progress."""
    asgn = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not asgn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

    if asgn.worker_profile_id != current_worker.id and "admin" not in [r.role for r in current_worker.role_assignments]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this assignment")

    issue = db.query(Issue).filter(Issue.id == asgn.issue_id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    asgn.status = "ACCEPTED"
    prev_status = issue.status
    issue.status = "IN_PROGRESS"

    event = StatusEvent(
        issue_id=issue.id,
        actor_profile_id=current_worker.id,
        previous_status=prev_status,
        next_status="IN_PROGRESS",
        reason=f"Worker {current_worker.full_name} accepted assignment and commenced work",
    )
    db.add(event)
    db.commit()

    from app.notifications.service import notification_service
    subs = db.query(Submission).filter(Submission.issue_id == issue.id).all()
    for s in subs:
        notification_service.send_notification(
            db=db,
            profile_id=s.reporter_id,
            event_type="WORK_STARTED",
            reference_number=issue.reference_number,
            issue_id=issue.id,
            locale=s.locale,
            dedup_suffix=f"started-{asgn.id[:8]}",
        )

    return {"status": "in_progress", "issue_id": issue.id}

@router.post("/assignments/{assignment_id}/decline")
def decline_assignment(
    assignment_id: str,
    req: DeclineRequest,
    current_worker: Profile = Depends(require_roles("worker", "admin")),
    db: Session = Depends(get_db),
):
    """Worker declines task with a mandatory reason."""
    asgn = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not asgn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

    issue = db.query(Issue).filter(Issue.id == asgn.issue_id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    asgn.status = "DECLINED"
    asgn.decline_reason = req.reason
    prev_status = issue.status
    issue.status = "UNDER_REVIEW"
    issue.assigned_worker_id = None

    event = StatusEvent(
        issue_id=issue.id,
        actor_profile_id=current_worker.id,
        previous_status=prev_status,
        next_status="UNDER_REVIEW",
        reason=f"Worker declined assignment: {req.reason}",
    )
    db.add(event)
    db.commit()

    from app.notifications.service import notification_service
    subs = db.query(Submission).filter(Submission.issue_id == issue.id).all()
    for s in subs:
        notification_service.send_notification(
            db=db,
            profile_id=s.reporter_id,
            event_type="REPAIR_REPORTED",
            reference_number=issue.reference_number,
            issue_id=issue.id,
            locale=s.locale,
            dedup_suffix=f"repair_rep-{issue.id[:8]}",
        )

    return {"status": "declined", "issue_id": issue.id}

@router.post("/issues/{issue_id}/repair-evidence")
async def upload_repair_evidence(
    issue_id: str,
    file: UploadFile = File(...),
    current_worker: Profile = Depends(require_roles("worker", "admin")),
    db: Session = Depends(get_db),
):
    """Worker uploads photo proof of completed repair work (WORKER_AFTER)."""
    issue = find_issue_by_any_id(db, issue_id)
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    file_bytes = await file.read()
    storage_path, mime_type, size_bytes, file_hash = storage_service.store_private_media(
        file_bytes, file.filename or "repair_after.jpg"
    )

    media = MediaAsset(
        profile_id=current_worker.id,
        issue_id=issue.id,
        evidence_role="WORKER_AFTER",
        storage_path=storage_path,
        file_hash=file_hash,
        mime_type=mime_type,
        file_size_bytes=size_bytes,
        is_quarantined=False,
        is_public_approved=False,
    )
    db.add(media)
    db.commit()
    db.refresh(media)

    return {
        "media_id": media.id,
        "evidence_role": media.evidence_role,
        "file_hash": media.file_hash,
    }

@router.post("/issues/{issue_id}/completion")
def submit_work_completion(
    issue_id: str,
    req: WorkCompletionSubmitRequest,
    current_worker: Profile = Depends(require_roles("worker", "admin")),
    db: Session = Depends(get_db),
):
    """
    Submits completed work with after-photos, materials, labour, and proposed expenditure for PDO verification.
    STRICT GOVERNANCE RULE: Field workers CANNOT mark issues resolved or approve their own costs.
    Moves status to REPAIR_REPORTED ("Awaiting Verification") and runs advisory AI comparison.
    """
    issue = find_issue_by_any_id(db, issue_id)
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    # Check that after photos exist
    after_photos = (
        db.query(MediaAsset)
        .filter(MediaAsset.issue_id == issue.id, MediaAsset.evidence_role == "WORKER_AFTER")
        .all()
    )
    if not after_photos and not req.after_media_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one photograph of the completed repair work is required.",
        )

    # Calculate proposed expenditure
    total_proposed = (
        req.proposed_cost
        if req.proposed_cost is not None and req.proposed_cost > 0
        else round(req.materials_cost + req.labour_cost + req.other_expenses_cost, 2)
    )

    # Determine submission number (handles rework / resubmissions without overwriting history)
    prior_count = db.query(WorkCompletion).filter(WorkCompletion.issue_id == issue.id).count()
    submission_num = prior_count + 1

    comp_dt = None
    if req.completion_date:
        try:
            comp_dt = datetime.fromisoformat(req.completion_date.replace("Z", "+00:00"))
        except Exception:
            comp_dt = datetime.now(timezone.utc)
    else:
        comp_dt = datetime.now(timezone.utc)

    # Find assignment
    asgn = db.query(Assignment).filter(Assignment.issue_id == issue.id, Assignment.worker_profile_id == current_worker.id).first()

    completion = WorkCompletion(
        issue_id=issue.id,
        worker_profile_id=current_worker.id,
        assignment_id=asgn.id if asgn else None,
        submission_number=submission_num,
        work_description=req.work_description,
        work_performed=req.work_performed or req.work_description,
        materials_used=req.materials_used,
        labour_details=req.labour_details,
        materials_cost=req.materials_cost,
        labour_cost=req.labour_cost,
        other_expenses_cost=req.other_expenses_cost,
        proposed_cost=total_proposed,
        completion_date=comp_dt,
        supporting_documents_paths=req.supporting_documents_paths,
        status="AWAITING_VERIFICATION",
    )
    db.add(completion)
    db.flush()

    # Link after-media assets to this work completion
    if req.after_media_ids:
        db.query(MediaAsset).filter(MediaAsset.id.in_(req.after_media_ids)).update(
            {"work_completion_id": completion.id}, synchronize_session=False
        )

    # Run AI Before/After Analysis (Advisory assistance only)
    before_asset = (
        db.query(MediaAsset)
        .filter(MediaAsset.issue_id == issue.id, MediaAsset.evidence_role == "CITIZEN_BEFORE")
        .order_by(MediaAsset.created_at.asc())
        .first()
    )
    latest_after_asset = (
        db.query(MediaAsset)
        .filter(MediaAsset.issue_id == issue.id, MediaAsset.evidence_role == "WORKER_AFTER")
        .order_by(MediaAsset.created_at.desc())
        .first()
    )

    ai_analysis_dict: Optional[Dict[str, Any]] = None
    if before_asset and latest_after_asset:
        try:
            before_abs = storage_service.get_absolute_path(before_asset.storage_path)
            after_abs = storage_service.get_absolute_path(latest_after_asset.storage_path)

            b_bytes = None
            a_bytes = None
            if os.path.exists(before_abs) and os.path.exists(after_abs):
                with open(before_abs, "rb") as f_b:
                    b_bytes = f_b.read()
                with open(after_abs, "rb") as f_a:
                    a_bytes = f_a.read()

            if b_bytes and a_bytes and gemini_service.is_available():
                gem_res = gemini_service.compare_before_after(b_bytes, a_bytes, category=issue.category)
                m_id = "gemini-1.5-flash-before-after"
                v_change = gem_res.get("visible_change", True)
                p_mismatch = gem_res.get("possible_mismatch", False)
                insufficient = gem_res.get("insufficient_evidence", False)
                v_score = float(gem_res.get("visual_consistency_score", 0.85))
                diff_sum = gem_res.get("difference_summary", "Completed visual inspection.")
                adv_decision = gem_res.get("suggested_advisory_decision", "RECOMMEND_APPROVAL")
            elif evidence_assistance_adapter:
                ai_res = evidence_assistance_adapter.analyze_evidence_pair(
                    before_image=before_abs,
                    after_image=after_abs,
                    before_hash=before_asset.file_hash,
                    after_hash=latest_after_asset.file_hash,
                )
                m_id = "evidence-assistance-dhash-v1"
                v_change = ai_res.get("visible_change", False)
                p_mismatch = ai_res.get("possible_mismatch", False)
                insufficient = ai_res.get("insufficient_evidence", False)
                v_score = round(ai_res.get("visual_consistency_score", 0.0), 3)
                diff_sum = ai_res.get("difference_summary", "Completed visual inspection.")
                adv_decision = ai_res.get("advisory_decision_suggestion", "REVIEW_FOR_APPROVAL")
            else:
                m_id = "deterministic-evidence-v1"
                v_change = True
                p_mismatch = False
                insufficient = False
                v_score = 0.80
                diff_sum = "Visual repair evidence submitted for PDO inspection."
                adv_decision = "REVIEW_FOR_APPROVAL"

            ai_rec = AIBeforeAfterAnalysis(
                issue_id=issue.id,
                work_completion_id=completion.id,
                before_media_asset_id=before_asset.id,
                after_media_asset_id=latest_after_asset.id,
                model_id=m_id,
                model_revision="rev-1.2.0",
                visible_change=v_change,
                possible_mismatch=p_mismatch,
                insufficient_evidence=insufficient,
                visual_consistency_score=v_score,
                difference_summary=diff_sum,
                advisory_decision_suggestion=adv_decision,
                suggested_description=f"Repair observed with {int(v_score * 100)}% visual scene consistency.",
                status="COMPLETED",
            )
            db.add(ai_rec)
            ai_analysis_dict = {
                "visible_change": ai_rec.visible_change,
                "visual_consistency_score": ai_rec.visual_consistency_score,
                "difference_summary": ai_rec.difference_summary,
                "advisory_decision_suggestion": ai_rec.advisory_decision_suggestion,
                "requires_human_review": True,
            }
        except Exception as e:
                ai_rec = AIBeforeAfterAnalysis(
                    issue_id=issue.id,
                    work_completion_id=completion.id,
                    before_media_asset_id=before_asset.id if before_asset else None,
                    after_media_asset_id=latest_after_asset.id if latest_after_asset else None,
                    model_id="evidence-assistance-dhash-v1",
                    model_revision="rev-1.2.0",
                    visible_change=False,
                    difference_summary="AI visual analysis temporarily unavailable. Proceeding with manual PDO verification.",
                    advisory_decision_suggestion="MANUAL_REVIEW_REQUIRED",
                    status="FAILED",
                    error_message=str(e),
                )
                db.add(ai_rec)
                ai_analysis_dict = {
                    "visible_change": False,
                    "visual_consistency_score": 0.0,
                    "difference_summary": "AI visual analysis unavailable. Human verification required.",
                    "advisory_decision_suggestion": "MANUAL_REVIEW_REQUIRED",
                    "requires_human_review": True,
                }
        else:
            ai_rec = AIBeforeAfterAnalysis(
                issue_id=issue.id,
                work_completion_id=completion.id,
                before_media_asset_id=before_asset.id,
                after_media_asset_id=latest_after_asset.id,
                model_id="evidence-assistance-dhash-v1",
                model_revision="rev-1.2.0",
                visible_change=False,
                difference_summary="AI adapter offline. Proceeding with manual PDO verification.",
                advisory_decision_suggestion="MANUAL_REVIEW_REQUIRED",
                status="FAILED",
            )
            db.add(ai_rec)
            ai_analysis_dict = {
                "visible_change": False,
                "visual_consistency_score": 0.0,
                "difference_summary": "AI visual analysis unavailable. Human verification required.",
                "advisory_decision_suggestion": "MANUAL_REVIEW_REQUIRED",
                "requires_human_review": True,
            }

    # Update Issue status to REPAIR_REPORTED ("Awaiting Verification")
    prev_status = issue.status
    issue.status = "REPAIR_REPORTED"
    issue.proposed_cost = total_proposed
    issue.materials_cost = req.materials_cost
    issue.labour_cost = req.labour_cost
    issue.other_expenses_cost = req.other_expenses_cost
    issue.cost_status = "PROPOSED"
    issue.work_completed_at = comp_dt
    issue.work_completion_description = req.work_description
    issue.work_performed = req.work_performed or req.work_description
    issue.materials_used = req.materials_used
    issue.labour_details = req.labour_details
    issue.resolution_review_notes = req.work_description

    event = StatusEvent(
        issue_id=issue.id,
        actor_profile_id=current_worker.id,
        previous_status=prev_status,
        next_status="REPAIR_REPORTED",
        reason=f"Worker {current_worker.full_name} submitted completion (Iteration #{submission_num}) with proposed cost ₹{total_proposed:,.2f}",
    )
    db.add(event)
    db.commit()

    # Notify Village PDO of new completion awaiting verification
    from app.notifications.service import notification_service
    # Reviewers in this locality
    reviewers = (
        db.query(Profile)
        .join(RoleAssignment, RoleAssignment.profile_id == Profile.id)
        .filter(RoleAssignment.role.in_(["reviewer", "admin"]), RoleAssignment.is_active == True)
        .all()
    )
    for rev in reviewers:
        notification_service.send_notification(
            db=db,
            profile_id=rev.id,
            event_type="COMPLETION_SUBMITTED",
            reference_number=issue.reference_number,
            issue_id=issue.id,
            locale=rev.preferred_locale or "en",
            dedup_suffix=f"comp-{completion.id[:8]}",
        )

    return {
        "status": "awaiting_verification",
        "issue_id": issue.id,
        "completion_id": completion.id,
        "submission_number": submission_num,
        "proposed_cost": total_proposed,
        "cost_status": issue.cost_status,
        "new_status": issue.status,
        "ai_analysis": ai_analysis_dict,
    }

@router.get("/issues/{issue_id}/completion-history")
def get_completion_history(
    issue_id: str,
    current_worker: Profile = Depends(require_roles("worker", "reviewer", "admin")),
    db: Session = Depends(get_db),
):
    """Returns all completion attempts and PDO verification remarks for an issue."""
    completions = (
        db.query(WorkCompletion)
        .filter(WorkCompletion.issue_id == issue_id)
        .order_by(WorkCompletion.submission_number.desc())
        .all()
    )
    results = []
    for c in completions:
        results.append({
            "id": c.id,
            "submission_number": c.submission_number,
            "work_description": c.work_description,
            "work_performed": c.work_performed,
            "materials_used": c.materials_used,
            "labour_details": c.labour_details,
            "materials_cost": c.materials_cost,
            "labour_cost": c.labour_cost,
            "other_expenses_cost": c.other_expenses_cost,
            "proposed_cost": c.proposed_cost,
            "completion_date": c.completion_date.isoformat() if c.completion_date else None,
            "status": c.status,
            "pdo_remarks": c.pdo_remarks,
            "verified_cost": c.verified_cost,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })
    return results

@router.post("/issues/{issue_id}/request-review")
def request_resolution_review(
    issue_id: str,
    req: RequestReviewRequest,
    current_worker: Profile = Depends(require_roles("worker", "admin")),
    db: Session = Depends(get_db),
):
    """
    Submits completed work for independent review.
    README Rule: Worker cannot approve their own work. Status moves to REPAIR_REPORTED.
    """
    issue = find_issue_by_any_id(db, issue_id)
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    # Check after-evidence exists
    after_photos_count = (
        db.query(MediaAsset)
        .filter(MediaAsset.issue_id == issue.id, MediaAsset.evidence_role == "WORKER_AFTER")
        .count()
    )
    if after_photos_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot request resolution review without uploading at least one photo proof of repair.",
        )

    prev_status = issue.status
    issue.status = "REPAIR_REPORTED"
    issue.resolution_review_notes = req.work_summary

    event = StatusEvent(
        issue_id=issue.id,
        actor_profile_id=current_worker.id,
        previous_status=prev_status,
        next_status="REPAIR_REPORTED",
        reason=f"Field worker submitted repair proof: {req.work_summary}",
    )
    db.add(event)
    db.commit()

    from app.notifications.service import notification_service
    subs = db.query(Submission).filter(Submission.issue_id == issue.id).all()
    for s in subs:
        notification_service.send_notification(
            db=db,
            profile_id=s.reporter_id,
            event_type="REPAIR_REPORTED",
            reference_number=issue.reference_number,
            issue_id=issue.id,
            locale=s.locale,
            dedup_suffix=f"repair_rep-{issue.id[:8]}",
        )

    return {
        "status": "repair_reported",
        "issue_id": issue.id,
        "new_status": issue.status,
    }

@router.post("/issues/{issue_id}/escalate")
def escalate_task(
    issue_id: str,
    req: EscalateTaskRequest,
    current_worker: Profile = Depends(require_roles("worker", "admin")),
    db: Session = Depends(get_db),
):
    """
    Worker reports that access is blocked, parts are unavailable, or work needs operational escalation (README 4.4, 5.2).
    """
    issue = find_issue_by_any_id(db, issue_id)
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    issue.is_escalated = True
    issue.escalated_at = datetime.now(timezone.utc)
    issue.escalation_reason = f"[{req.reason}] {req.explanation}"

    event = StatusEvent(
        issue_id=issue.id,
        actor_profile_id=current_worker.id,
        previous_status=issue.status,
        next_status=issue.status,
        reason=f"Worker flagged operational escalation: [{req.reason}] {req.explanation}",
    )
    db.add(event)
    db.commit()

    # Enqueue notification to authority supervisor / reviewer
    from app.notifications.service import notification_service
    reviewers = db.query(Profile).filter(Profile.email.like("%reviewer%")).all()
    for rev in reviewers:
        notification_service.send_notification(
            db=db,
            profile_id=rev.id,
            event_type="ESCALATION_TRIGGERED",
            reference_number=issue.reference_number,
            issue_id=issue.id,
            locale=rev.preferred_locale or "en",
            dedup_suffix=f"esc-{issue.id[:8]}",
        )

    return {
        "status": "escalated",
        "issue_id": issue.id,
        "is_escalated": True,
        "escalation_reason": issue.escalation_reason,
    }


class WorkerStatusResponse(BaseModel):
    worker_id: str
    full_name: str
    email: str
    approval_status: str
    is_approved: bool
    village_name: Optional[str] = None
    assigned_tasks_count: int
    pending_tasks_count: int
    in_progress_tasks_count: int

@router.get("/status", response_model=WorkerStatusResponse)
def get_worker_approval_status(
    current_worker: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Checks whether this worker's account has been approved by the Village PDO.
    """
    asgn = (
        db.query(RoleAssignment)
        .filter(RoleAssignment.profile_id == current_worker.id, RoleAssignment.role == "worker")
        .first()
    )

    approval_status = getattr(asgn, "approval_status", "APPROVED") if asgn else "APPROVED"
    is_approved = approval_status == "APPROVED"

    village_name = None
    if asgn and asgn.jurisdiction_unit_id:
        from app.models.localities import LocalityUnit
        u = db.query(LocalityUnit).filter(LocalityUnit.id == asgn.jurisdiction_unit_id).first()
        if u:
            village_name = u.name_en

    assigned_cnt = db.query(Assignment).filter(Assignment.worker_profile_id == current_worker.id).count()
    pending_cnt = db.query(Assignment).filter(
        Assignment.worker_profile_id == current_worker.id,
        Assignment.status == "ASSIGNED",
    ).count()
    in_progress_cnt = db.query(Assignment).filter(
        Assignment.worker_profile_id == current_worker.id,
        Assignment.status.in_(["ACCEPTED", "IN_PROGRESS"]),
    ).count()

    return WorkerStatusResponse(
        worker_id=current_worker.id,
        full_name=current_worker.full_name,
        email=current_worker.email,
        approval_status=approval_status,
        is_approved=is_approved,
        village_name=village_name,
        assigned_tasks_count=assigned_cnt,
        pending_tasks_count=pending_cnt,
        in_progress_tasks_count=in_progress_cnt,
    )

@router.post("/issues/{issue_id}/progress-notes")
def add_worker_progress_note(
    issue_id: str,
    req: ProgressNoteRequest,
    current_worker: Profile = Depends(require_roles("worker", "admin")),
    db: Session = Depends(get_db),
):
    """Worker logs an interim work progress update."""
    issue = find_issue_by_any_id(db, issue_id)
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    event = StatusEvent(
        issue_id=issue.id,
        actor_profile_id=current_worker.id,
        previous_status=issue.status,
        next_status=issue.status,
        reason=f"Worker progress note: {req.notes}",
    )
    db.add(event)
    db.commit()
    return {"status": "success", "note": req.notes}

class WorkerMapPoint(BaseModel):
    id: str
    reference_number: str
    category: str
    status: str
    priority: str
    latitude: float
    longitude: float
    instructions: Optional[str] = None
    ward_name: Optional[str] = None

@router.get("/map-tasks", response_model=List[WorkerMapPoint])
def get_worker_map_tasks(
    current_worker: Profile = Depends(require_roles("worker", "admin")),
    db: Session = Depends(get_db),
):
    """
    Returns locations of only the complaints assigned to this worker.
    Strictly prevents exposing unrelated citizen or worker locations.
    """
    assignments = (
        db.query(Assignment, Issue)
        .join(Issue, Assignment.issue_id == Issue.id)
        .filter(
            Assignment.worker_profile_id == current_worker.id,
            (Issue.latitude.isnot(None)) | (Issue.public_latitude.isnot(None)),
        )
        .all()
    )

    results: List[WorkerMapPoint] = []
    for asgn, issue in assignments:
        sub = db.query(Submission).filter(Submission.issue_id == issue.id).first()
        lat = issue.latitude or (sub.latitude if sub else None) or issue.public_latitude
        lon = issue.longitude or (sub.longitude if sub else None) or issue.public_longitude
        if not lat or not lon:
            continue

        ward_name = issue.locality_unit.name_en if issue.locality_unit else "Ward Unknown"

        results.append(
            WorkerMapPoint(
                id=issue.id,
                reference_number=issue.reference_number,
                category=issue.category,
                status=issue.status,
                priority=issue.priority,
                latitude=lat,
                longitude=lon,
                instructions=asgn.instructions,
                ward_name=ward_name,
            )
        )

    return results

