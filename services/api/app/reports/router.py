import random
import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.users import Profile, RoleAssignment
from app.models.localities import LocalityUnit, Organization
from app.models.issues import (
    Issue,
    Submission,
    MediaAsset,
    StatusEvent,
    Job,
)
from app.storage.service import storage_service
from app.auth.dependencies import get_current_user, require_roles
from app.reports.schemas import (
    DraftCreateRequest,
    DraftUpdateRequest,
    SubmitReportRequest,
    ReportResponse,
    MediaAssetResponse,
    StatusEventResponse,
)

router = APIRouter(prefix="/reports", tags=["Citizen Reporting & Evidence"])

def generate_tracking_id() -> str:
    year = datetime.now(timezone.utc).year
    rand_suffix = random.randint(10000, 99999)
    return f"FP-{year}-{rand_suffix}"

def build_report_response(submission: Submission, issue: Optional[Issue], db: Session) -> ReportResponse:
    media = (
        db.query(MediaAsset)
        .filter(MediaAsset.submission_id == submission.id)
        .all()
    )
    media_responses = [
        MediaAssetResponse(
            id=m.id,
            evidence_role=m.evidence_role,
            mime_type=m.mime_type,
            file_size_bytes=m.file_size_bytes,
            file_hash=m.file_hash,
            is_quarantined=m.is_quarantined,
        )
        for m in media
    ]

    events = []
    if issue:
        status_events = (
            db.query(StatusEvent)
            .filter(StatusEvent.issue_id == issue.id)
            .order_by(StatusEvent.created_at.asc())
            .all()
        )
        events = [
            StatusEventResponse(
                previous_status=e.previous_status,
                next_status=e.next_status,
                reason=e.reason,
                created_at=e.created_at,
            )
            for e in status_events
        ]

    current_status = issue.status if issue else "DRAFT"

    return ReportResponse(
        id=submission.id,
        tracking_id=submission.tracking_id,
        category=submission.category,
        description=submission.description,
        locale=submission.locale,
        status=current_status,
        village_name=submission.village_name,
        ward_name=submission.ward_name,
        locality_unit_id=submission.locality_unit_id,
        latitude=submission.latitude,
        longitude=submission.longitude,
        created_at=submission.created_at,
        media_assets=media_responses,
        timeline=events,
    )

@router.post("/drafts", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
def create_draft(
    req: DraftCreateRequest,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Creates a new draft complaint for the citizen.
    Persists draft before any AI or external calls.
    """
    org = db.query(Organization).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Pilot organization not initialized. Run seed script first.",
        )

    tracking_id = generate_tracking_id()

    # 1. Create linked Issue with DRAFT status
    issue = Issue(
        reference_number=tracking_id,
        category=req.category,
        status="DRAFT",
        priority="MEDIUM",
        organization_id=org.id,
        locality_unit_id=req.locality_unit_id,
        latitude=req.latitude,
        longitude=req.longitude,
        public_latitude=round(req.latitude, 3) if req.latitude else None,
        public_longitude=round(req.longitude, 3) if req.longitude else None,
    )
    db.add(issue)
    db.flush()

    # 2. Create citizen Submission record
    submission = Submission(
        tracking_id=tracking_id,
        reporter_id=current_user.id,
        issue_id=issue.id,
        category=req.category,
        description=req.description,
        locale=req.locale or current_user.preferred_locale or "en",
        original_text=req.description,
        locality_unit_id=req.locality_unit_id,
        village_name=req.village_name,
        ward_name=req.ward_name,
        latitude=req.latitude,
        longitude=req.longitude,
    )
    db.add(submission)

    # 3. Create initial status event
    event = StatusEvent(
        issue_id=issue.id,
        actor_profile_id=current_user.id,
        previous_status=None,
        next_status="DRAFT",
        reason="Citizen draft initialized",
    )
    db.add(event)
    db.commit()
    db.refresh(submission)
    db.refresh(issue)

    return build_report_response(submission, issue, db)

@router.patch("/{id}/draft", response_model=ReportResponse)
def update_draft(
    id: str,
    req: DraftUpdateRequest,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Updates an existing draft before final submission."""
    submission = db.query(Submission).filter(Submission.id == id).first()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")

    if submission.reporter_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to edit this draft",
        )

    issue = db.query(Issue).filter(Issue.id == submission.issue_id).first()
    if issue and issue.status != "DRAFT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot edit report that is already {issue.status}",
        )

    # Apply updates
    if req.category is not None:
        submission.category = req.category
        if issue:
            issue.category = req.category
    if req.description is not None:
        submission.description = req.description
        submission.original_text = req.description
    if req.locale is not None:
        submission.locale = req.locale
    if req.village_name is not None:
        submission.village_name = req.village_name
    if req.ward_name is not None:
        submission.ward_name = req.ward_name
    if req.locality_unit_id is not None:
        submission.locality_unit_id = req.locality_unit_id
        if issue:
            issue.locality_unit_id = req.locality_unit_id
    if req.latitude is not None:
        submission.latitude = req.latitude
        if issue:
            issue.latitude = req.latitude
            issue.public_latitude = round(req.latitude, 3)
    if req.longitude is not None:
        submission.longitude = req.longitude
        if issue:
            issue.longitude = req.longitude
            issue.public_longitude = round(req.longitude, 3)

    db.commit()
    db.refresh(submission)
    if issue:
        db.refresh(issue)

    return build_report_response(submission, issue, db)

@router.post("/{id}/media", response_model=MediaAssetResponse)
async def upload_report_media(
    id: str,
    file: UploadFile = File(...),
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Validates and uploads private photo evidence for a complaint draft.
    Validates actual magic bytes, dimensions, and computes SHA-256 hash.
    """
    submission = db.query(Submission).filter(Submission.id == id).first()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")

    if submission.reporter_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to add media to this draft",
        )

    file_bytes = await file.read()
    storage_path, mime_type, size_bytes, file_hash = storage_service.store_private_media(
        file_bytes, file.filename or "evidence.jpg"
    )

    media = MediaAsset(
        profile_id=current_user.id,
        submission_id=submission.id,
        issue_id=submission.issue_id,
        evidence_role="CITIZEN_BEFORE",
        storage_path=storage_path,
        file_hash=file_hash,
        mime_type=mime_type,
        file_size_bytes=size_bytes,
        is_quarantined=True,
        is_public_approved=False,
    )
    db.add(media)
    db.commit()
    db.refresh(media)

    return MediaAssetResponse(
        id=media.id,
        evidence_role=media.evidence_role,
        mime_type=media.mime_type,
        file_size_bytes=media.file_size_bytes,
        file_hash=media.file_hash,
        is_quarantined=media.is_quarantined,
    )

@router.post("/{id}/submit", response_model=ReportResponse)
def submit_report(
    id: str,
    req: SubmitReportRequest,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Finalizes submission from DRAFT to SUBMITTED.
    Enforces evidence requirement and audit events.
    """
    submission = db.query(Submission).filter(Submission.id == id).first()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")

    if submission.reporter_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to submit this report",
        )

    issue = db.query(Issue).filter(Issue.id == submission.issue_id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Associated issue missing")

    # Idempotency: if already submitted, return current state without error
    if issue.status != "DRAFT":
        return build_report_response(submission, issue, db)

    # Evidence check: must have at least one photo
    media_count = db.query(MediaAsset).filter(MediaAsset.submission_id == submission.id).count()
    if media_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Evidence photo is required before submitting a complaint.",
        )

    # Update anonymity preference
    if req.is_anonymous:
        submission.is_anonymous = True

    # Transition status
    issue.status = "SUBMITTED"

    event = StatusEvent(
        issue_id=issue.id,
        actor_profile_id=current_user.id,
        previous_status="DRAFT",
        next_status="SUBMITTED",
        reason="Citizen completed submission with photo evidence",
    )
    db.add(event)

    # Create persistent job queue item for background triage
    job = Job(
        task_name="triage_submission",
        payload_json=f'{{"submission_id": "{submission.id}", "issue_id": "{issue.id}"}}',
        status="QUEUED",
    )
    db.add(job)

    db.commit()
    db.refresh(submission)
    db.refresh(issue)

    # In-app notification for submission received
    from app.notifications.service import notification_service
    notification_service.send_notification(
        db=db,
        profile_id=current_user.id,
        event_type="SUBMISSION_RECEIVED",
        reference_number=submission.tracking_id,
        issue_id=issue.id,
        locale=submission.locale,
        dedup_suffix="initial-submit",
    )

    return build_report_response(submission, issue, db)

@router.get("", response_model=List[ReportResponse])
def list_my_reports(
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lists complaints submitted by the authenticated citizen."""
    query = (
        db.query(Submission)
        .join(Issue, Submission.issue_id == Issue.id)
        .filter(Submission.reporter_id == current_user.id)
    )

    if status_filter and status_filter != "ALL":
        query = query.filter(Issue.status == status_filter)

    if search:
        search_fmt = f"%{search.lower()}%"
        query = query.filter(
            (Submission.tracking_id.ilike(search_fmt))
            | (Submission.category.ilike(search_fmt))
            | (Submission.village_name.ilike(search_fmt))
            | (Submission.description.ilike(search_fmt))
        )

    submissions = query.order_by(Submission.created_at.desc()).all()
    results = []
    for s in submissions:
        issue = db.query(Issue).filter(Issue.id == s.issue_id).first()
        results.append(build_report_response(s, issue, db))
    return results

@router.get("/{id}", response_model=ReportResponse)
def get_report_detail(
    id: str,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns full complaint details for the owner or authorized staff.
    Blocks unauthorized citizens from reading private reports (Privacy rule Section 13.1).
    """
    submission = db.query(Submission).filter((Submission.id == id) | (Submission.tracking_id == id)).first()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    # Authorization check
    is_owner = submission.reporter_id == current_user.id
    user_roles = [r.role for r in current_user.role_assignments if r.is_active]
    is_staff = any(r in ["reviewer", "worker", "admin"] for r in user_roles)

    if not is_owner and not is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You cannot view private reports belonging to another citizen",
        )

    issue = db.query(Issue).filter(Issue.id == submission.issue_id).first()
    return build_report_response(submission, issue, db)

@router.get("/media/{media_id}/view")
def view_private_media(
    media_id: str,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Securely serves private evidence only to the owner or authorized staff.
    Strips EXIF/GPS, enforces access control.
    """
    media = db.query(MediaAsset).filter(MediaAsset.id == media_id).first()
    if not media:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media asset not found")

    is_owner = media.profile_id == current_user.id
    user_roles = [r.role for r in current_user.role_assignments if r.is_active]
    is_staff = any(r in ["reviewer", "worker", "admin"] for r in user_roles)

    if not is_owner and not is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Private citizen evidence is restricted",
        )

    abs_path = storage_service.get_absolute_path(media.storage_path)
    return FileResponse(abs_path, media_type=media.mime_type)

from pydantic import BaseModel
class DisputeRequest(BaseModel):
    reason: str

@router.post("/{id}/dispute")
def dispute_report(
    id: str,
    req: DisputeRequest,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Citizen disputes resolution or repair proof.
    Transitions issue status to REOPENED and creates a formal Dispute record.
    """
    submission = db.query(Submission).filter((Submission.id == id) | (Submission.tracking_id == id)).first()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    if submission.reporter_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the reporting citizen can dispute this complaint")

    issue = db.query(Issue).filter(Issue.id == submission.issue_id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Associated issue missing")

    prev_status = issue.status
    issue.status = "REOPENED"

    from app.models.issues import Dispute, Feedback
    from app.notifications.service import notification_service

    dispute = Dispute(
        issue_id=issue.id,
        citizen_profile_id=current_user.id,
        reason=req.reason,
        status="OPEN",
    )
    db.add(dispute)

    event = StatusEvent(
        issue_id=issue.id,
        actor_profile_id=current_user.id,
        previous_status=prev_status,
        next_status="REOPENED",
        reason=f"Citizen disputed resolution: {req.reason}",
    )
    db.add(event)
    db.commit()

    # In-app notification for dispute
    notification_service.send_notification(
        db=db,
        profile_id=current_user.id,
        event_type="ISSUE_REOPENED",
        reference_number=issue.reference_number,
        issue_id=issue.id,
        locale=submission.locale,
        dedup_suffix=f"dispute-{dispute.id[:8]}",
    )

    return {
        "status": "reopened",
        "issue_id": issue.id,
        "new_status": issue.status,
        "dispute_id": dispute.id,
    }

class FeedbackRequest(BaseModel):
    rating: int  # 1 to 5
    comment: Optional[str] = None
    is_satisfied: bool = True

@router.post("/{id}/feedback")
def submit_report_feedback(
    id: str,
    req: FeedbackRequest,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Citizen submits post-repair feedback and rating (1-5 stars) for a resolved complaint."""
    if req.rating < 1 or req.rating > 5:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rating must be between 1 and 5")

    submission = db.query(Submission).filter((Submission.id == id) | (Submission.tracking_id == id)).first()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    if submission.reporter_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the reporting citizen can provide feedback")

    issue = db.query(Issue).filter(Issue.id == submission.issue_id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    if issue.status != "RESOLVED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Feedback can only be submitted for RESOLVED issues. Current status: {issue.status}",
        )

    from app.models.issues import Feedback
    # Check if feedback already submitted
    existing_fb = db.query(Feedback).filter(
        Feedback.issue_id == issue.id,
        Feedback.citizen_profile_id == current_user.id,
    ).first()

    if existing_fb:
        existing_fb.rating = req.rating
        existing_fb.comment = req.comment
        existing_fb.is_satisfied = req.is_satisfied
        db.commit()
        return {"status": "updated", "feedback_id": existing_fb.id}

    fb = Feedback(
        id=str(uuid.uuid4()),
        issue_id=issue.id,
        citizen_profile_id=current_user.id,
        rating=req.rating,
        comment=req.comment,
        is_satisfied=req.is_satisfied,
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)

    return {"status": "created", "feedback_id": fb.id}

@router.get("/{id}/feedback")
def get_report_feedback(
    id: str,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves citizen feedback for this issue."""
    submission = db.query(Submission).filter((Submission.id == id) | (Submission.tracking_id == id)).first()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    from app.models.issues import Feedback
    fb = db.query(Feedback).filter(Feedback.issue_id == submission.issue_id).first()
    if not fb:
        return {"has_feedback": False}

    return {
        "has_feedback": True,
        "rating": fb.rating,
        "comment": fb.comment,
        "is_satisfied": fb.is_satisfied,
        "created_at": fb.created_at,
    }

