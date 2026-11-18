from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.users import Profile
from app.models.issues import (
    Issue,
    Submission,
    MediaAsset,
    Assignment,
    StatusEvent,
)
from app.storage.service import storage_service
from app.auth.dependencies import get_current_user, require_roles

router = APIRouter(prefix="/worker", tags=["Field Worker Operations"])

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

class ProgressNoteRequest(BaseModel):
    notes: str

class DeclineRequest(BaseModel):
    reason: str

class EscalateTaskRequest(BaseModel):
    reason: str  # BLOCKED, NEEDS_MATERIALS, INACCESSIBLE, OTHER
    explanation: str

class RequestReviewRequest(BaseModel):
    work_summary: str

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
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
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
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
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
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
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
