import random
import os
import sys
import uuid
import json
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
    DuplicateCandidate,
    LocationAuditLog,
)
from app.storage.service import storage_service
from app.auth.dependencies import get_current_user, get_optional_current_user, require_roles
from app.reports.schemas import (
    DraftCreateRequest,
    DraftUpdateRequest,
    SubmitReportRequest,
    ReportResponse,
    MediaAssetResponse,
    StatusEventResponse,
    DuplicateSuggestionItem,
    CheckDuplicatesRequest,
    OfflineDraftSyncItem,
    SyncReportResponse,
)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from workers.adapters.duplicate.similarity import rank_duplicate_candidate

router = APIRouter(prefix="/reports", tags=["Citizen Reporting & Evidence"])

def generate_tracking_id(db: Optional[Session] = None) -> str:
    year = datetime.now(timezone.utc).year
    for _ in range(20):
        rand_suffix = random.randint(10000, 99999)
        candidate = f"GS-{year}-{rand_suffix}"
        if db is not None:
            collision = db.query(Issue).filter(Issue.reference_number == candidate).first()
            if not collision:
                return candidate
        else:
            return candidate
    return f"GS-{year}-{random.randint(10000, 99999)}{uuid.uuid4().hex[:2].upper()}"

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
        issue_id=issue.id if issue else submission.issue_id,
        tracking_id=submission.tracking_id,
        category=submission.category,
        description=submission.description,
        locale=submission.locale,
        status=current_status,
        village_name=submission.village_name,
        ward_name=submission.ward_name,
        taluk_name=getattr(submission, "taluk_name", "Belagavi Taluk") or "Belagavi Taluk",
        locality_unit_id=submission.locality_unit_id,
        latitude=submission.latitude,
        longitude=submission.longitude,
        reporter_name=getattr(submission, "reporter_name", None),
        reporter_phone=getattr(submission, "reporter_phone", None),
        is_guest=bool(getattr(submission, "is_guest", False)),
        location_method=getattr(submission, "location_method", "GPS_VERIFIED") or "GPS_VERIFIED",
        gps_accuracy=getattr(submission, "gps_accuracy", None),
        voice_transcription=getattr(submission, "voice_transcription", None),
        annotated_media_id=getattr(submission, "annotated_media_id", None),
        ai_category_suggestion=getattr(submission, "ai_category_suggestion", None),
        ai_confidence=getattr(submission, "ai_confidence", None),
        confirmed_latitude=getattr(submission, "confirmed_latitude", None),
        confirmed_longitude=getattr(submission, "confirmed_longitude", None),
        confirmed_village=getattr(submission, "confirmed_village", None),
        confirmed_address=getattr(submission, "confirmed_address", None),
        confirmation_method=getattr(submission, "confirmation_method", "CITIZEN_CONFIRMED") or "CITIZEN_CONFIRMED",
        jurisdiction_status=getattr(submission, "jurisdiction_status", "VERIFIED") or "VERIFIED",
        location_conflict_flag=bool(getattr(submission, "location_conflict_flag", False)),
        location_conflict_details=getattr(submission, "location_conflict_details", None),
        ocr_extracted_text=getattr(submission, "ocr_extracted_text", None),
        ocr_detections_json=getattr(submission, "ocr_detections_json", None),
        landmark_candidates_json=getattr(submission, "landmark_candidates_json", None),
        photo_location_status=getattr(submission, "photo_location_status", None),
        photo_location_provider=getattr(submission, "photo_location_provider", None),
        gps_timestamp=getattr(submission, "gps_timestamp", None),
        detected_village=getattr(submission, "detected_village", None),
        detected_taluk=getattr(submission, "detected_taluk", None),
        detected_district=getattr(submission, "detected_district", None),
        detected_state=getattr(submission, "detected_state", None),
        detected_country=getattr(submission, "detected_country", "India") or "India",
        detected_postal_code=getattr(submission, "detected_postal_code", None),
        google_place_id=getattr(submission, "google_place_id", None),
        geocoding_status=getattr(submission, "geocoding_status", None),
        location_confirmation_status=getattr(submission, "location_confirmation_status", "UNCONFIRMED") or "UNCONFIRMED",
        clarification_message=getattr(issue, "clarification_message", None) if issue else None,
        clarification_response=getattr(issue, "clarification_response", None) if issue else None,
        rejection_reason=getattr(issue, "rejection_reason", None) if issue else None,
        rejection_by_id=getattr(issue, "rejection_by_id", None) if issue else None,
        is_demo=bool(getattr(issue, "is_demo", False)) if issue else bool(getattr(submission, "is_demo", False)),
        verified_cost=getattr(issue, "verified_cost", None) if issue else None,
        cost_status=getattr(issue, "cost_status", None) if issue else None,
        work_completed_at=getattr(issue, "work_completed_at", None) if issue else None,
        created_at=submission.created_at,
        media_assets=media_responses,
        timeline=events,
    )

@router.post("/drafts", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
def create_draft(
    req: DraftCreateRequest,
    current_user: Optional[Profile] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """
    Creates a new draft complaint for authenticated citizen or guest.
    Persists draft before any AI or external calls.
    """
    org = db.query(Organization).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Pilot organization not initialized. Run seed script first.",
        )

    # Resolve or create guest citizen profile if unauthenticated
    is_guest = bool(req.is_guest) or (current_user is None)
    if not current_user:
        clean_phone = "".join([c for c in (req.reporter_phone or "") if c.isdigit() or c == "+"])
        guest_email = f"guest_{clean_phone[-10:] if len(clean_phone) >= 10 else uuid.uuid4().hex[:8]}@gramaseva.internal"
        guest_profile = db.query(Profile).filter(Profile.email == guest_email).first()
        if not guest_profile:
            guest_profile = Profile(
                id=str(uuid.uuid4()),
                email=guest_email,
                password_hash="GUEST_CITIZEN_NO_LOGIN",
                full_name=req.reporter_name or "Guest Citizen",
                phone_number=clean_phone or None,
                preferred_locale=req.locale or "en",
                taluk=req.taluk_name or "Belagavi Taluk",
                is_active=True,
            )
            db.add(guest_profile)
            db.flush()
            ra = RoleAssignment(
                profile_id=guest_profile.id,
                role="citizen",
                is_active=True,
            )
            db.add(ra)
            db.flush()
        current_user = guest_profile
        is_guest = True

    tracking_id = generate_tracking_id(db)

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
        taluk_name=req.taluk_name or "Belagavi Taluk",
        latitude=req.latitude,
        longitude=req.longitude,
        reporter_name=req.reporter_name or current_user.full_name,
        reporter_phone=req.reporter_phone or current_user.phone_number,
        is_guest=is_guest,
        location_method=req.location_method or "GPS_VERIFIED",
        gps_accuracy=req.gps_accuracy,
        voice_transcription=req.voice_transcription,
        annotated_media_id=req.annotated_media_id,
        ai_category_suggestion=req.ai_category_suggestion,
        ai_confidence=req.ai_confidence,
        confirmed_latitude=req.confirmed_latitude,
        confirmed_longitude=req.confirmed_longitude,
        confirmed_village=req.confirmed_village,
        confirmed_address=req.confirmed_address,
        confirmation_method=req.confirmation_method or "CITIZEN_CONFIRMED",
        jurisdiction_status=req.jurisdiction_status or "VERIFIED",
        location_conflict_flag=bool(req.location_conflict_flag),
        location_conflict_details=req.location_conflict_details,
        ocr_extracted_text=req.ocr_extracted_text,
        ocr_detections_json=req.ocr_detections_json,
        landmark_candidates_json=req.landmark_candidates_json,
        photo_location_status=req.photo_location_status,
        photo_location_provider=req.photo_location_provider,
        gps_timestamp=req.gps_timestamp,
        detected_village=req.detected_village,
        detected_taluk=req.detected_taluk,
        detected_district=req.detected_district,
        detected_state=req.detected_state,
        detected_country=req.detected_country or "India",
        detected_postal_code=req.detected_postal_code,
        google_place_id=req.google_place_id,
        geocoding_status=req.geocoding_status,
        location_confirmation_status=req.location_confirmation_status or "UNCONFIRMED",
    )
    if req.jurisdiction_status:
        issue.jurisdiction_status = req.jurisdiction_status
    if req.location_conflict_flag is not None:
        issue.has_location_conflict = bool(req.location_conflict_flag)
    if req.location_conflict_details:
        issue.location_conflict_details = req.location_conflict_details
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
    if req.confirmed_latitude is not None:
        submission.confirmed_latitude = req.confirmed_latitude
    if req.confirmed_longitude is not None:
        submission.confirmed_longitude = req.confirmed_longitude
    if req.confirmed_village is not None:
        submission.confirmed_village = req.confirmed_village
    if req.confirmed_address is not None:
        submission.confirmed_address = req.confirmed_address
    if req.confirmation_method is not None:
        submission.confirmation_method = req.confirmation_method
    if req.jurisdiction_status is not None:
        submission.jurisdiction_status = req.jurisdiction_status
        if issue:
            issue.jurisdiction_status = req.jurisdiction_status
    if req.location_conflict_flag is not None:
        submission.location_conflict_flag = req.location_conflict_flag
        if issue:
            issue.has_location_conflict = req.location_conflict_flag
    if req.location_conflict_details is not None:
        submission.location_conflict_details = req.location_conflict_details
        if issue:
            issue.location_conflict_details = req.location_conflict_details
    if req.ocr_extracted_text is not None:
        submission.ocr_extracted_text = req.ocr_extracted_text
    if req.ocr_detections_json is not None:
        submission.ocr_detections_json = req.ocr_detections_json
    if req.landmark_candidates_json is not None:
        submission.landmark_candidates_json = req.landmark_candidates_json
    if req.photo_location_status is not None:
        submission.photo_location_status = req.photo_location_status
    if req.photo_location_provider is not None:
        submission.photo_location_provider = req.photo_location_provider
    if req.gps_timestamp is not None:
        submission.gps_timestamp = req.gps_timestamp

    db.commit()
    db.refresh(submission)
    if issue:
        db.refresh(issue)

    return build_report_response(submission, issue, db)

@router.post("/{id}/media", response_model=MediaAssetResponse)
async def upload_report_media(
    id: str,
    file: UploadFile = File(...),
    current_user: Optional[Profile] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """
    Validates and uploads private photo evidence for a complaint draft.
    Validates actual magic bytes, dimensions, and computes SHA-256 hash.
    Supports authenticated citizens and guest submissions.
    """
    submission = db.query(Submission).filter(Submission.id == id).first()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")

    if current_user and submission.reporter_id != current_user.id and not getattr(submission, "is_guest", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to add media to this draft",
        )

    actor_id = current_user.id if current_user else submission.reporter_id

    file_bytes = await file.read()
    storage_path, mime_type, size_bytes, file_hash = storage_service.store_private_media(
        file_bytes, file.filename or "evidence.jpg"
    )

    media = MediaAsset(
        profile_id=actor_id,
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
    current_user: Optional[Profile] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """
    Finalizes submission from DRAFT to SUBMITTED.
    Enforces evidence requirement and audit events.
    Supports authenticated citizens and guest submissions.
    """
    submission = db.query(Submission).filter(Submission.id == id).first()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")

    if current_user and submission.reporter_id != current_user.id and not getattr(submission, "is_guest", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to submit this report",
        )

    actor_id = current_user.id if current_user else submission.reporter_id

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

    # Milestone 1: Handle Confirmed Duplicate Linking
    if req.duplicate_decision == "CONFIRMED_DUPLICATE" and req.duplicate_target_issue_id:
        target_issue = db.query(Issue).filter(Issue.id == req.duplicate_target_issue_id).first()
        if target_issue:
            old_draft_issue = issue
            # Detach submission from old issue collection before re-linking
            if submission in old_draft_issue.submissions:
                old_draft_issue.submissions.remove(submission)
            submission.issue_id = target_issue.id
            if target_issue not in old_draft_issue.submissions:
                target_issue.submissions.append(submission)

            # Link uploaded media assets to target issue
            for media in db.query(MediaAsset).filter(MediaAsset.submission_id == submission.id).all():
                if media in old_draft_issue.media_assets:
                    old_draft_issue.media_assets.remove(media)
                media.issue_id = target_issue.id

            # Record duplicate candidate decision
            dup = DuplicateCandidate(
                submission_id=submission.id,
                target_issue_id=target_issue.id,
                detection_method="citizen_confirmed_duplicate",
                decision="CONFIRMED_DUPLICATE",
                notes=f"Citizen confirmed report {submission.tracking_id} links to existing issue {target_issue.reference_number}",
            )
            db.add(dup)

            # Record StatusEvent on existing physical issue
            event = StatusEvent(
                issue_id=target_issue.id,
                actor_profile_id=current_user.id,
                previous_status=target_issue.status,
                next_status=target_issue.status,
                reason=f"Additional citizen report {submission.tracking_id} confirmed as duplicate and linked.",
            )
            db.add(event)

            # Clean up redundant placeholder draft issue
            if old_draft_issue.id != target_issue.id:
                db.query(StatusEvent).filter(StatusEvent.issue_id == old_draft_issue.id).delete()
                db.delete(old_draft_issue)

            db.commit()
            db.refresh(submission)
            db.refresh(target_issue)

            from app.notifications.service import notification_service
            notification_service.send_notification(
                db=db,
                profile_id=current_user.id,
                event_type="SUBMISSION_RECEIVED",
                reference_number=submission.tracking_id,
                issue_id=target_issue.id,
                locale=submission.locale,
                dedup_suffix="duplicate-link",
            )

            return build_report_response(submission, target_issue, db)

    # Handle Uncertain Duplicate (Needs Human Review) vs Rejected Different
    if req.duplicate_decision == "UNCERTAIN_NEEDS_REVIEW" and req.duplicate_target_issue_id:
        dup = DuplicateCandidate(
            submission_id=submission.id,
            target_issue_id=req.duplicate_target_issue_id,
            detection_method="spatial_and_visual_candidate",
            decision="UNCERTAIN_NEEDS_REVIEW",
            notes="Citizen flagged uncertainty regarding duplicate candidate; requires reviewer adjudication.",
        )
        db.add(dup)
        event_reason = f"Citizen completed submission. Flagged possible duplicate with issue {req.duplicate_target_issue_id} (Uncertain - reviewer check requested)."
    elif req.duplicate_decision == "REJECTED_DIFFERENT" and req.duplicate_target_issue_id:
        dup = DuplicateCandidate(
            submission_id=submission.id,
            target_issue_id=req.duplicate_target_issue_id,
            detection_method="spatial_and_visual_candidate",
            decision="REJECTED_DIFFERENT",
            notes="Citizen confirmed issue is distinct.",
        )
        db.add(dup)
        event_reason = "Citizen completed submission (Confirmed distinct issue)."
    else:
        event_reason = "Citizen completed submission with photo evidence"

    # Ensure all media assets for this submission are attached to the issue
    for m in db.query(MediaAsset).filter(MediaAsset.submission_id == submission.id).all():
        m.issue_id = issue.id

    # Transition status
    issue.status = "SUBMITTED"

    event = StatusEvent(
        issue_id=issue.id,
        actor_profile_id=current_user.id,
        previous_status="DRAFT",
        next_status="SUBMITTED",
        reason=event_reason,
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
        profile_id=actor_id,
        event_type="SUBMISSION_RECEIVED",
        reference_number=submission.tracking_id,
        issue_id=issue.id,
        locale=submission.locale,
        dedup_suffix="initial-submit",
    )

    return build_report_response(submission, issue, db)

@router.post("/submit", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
def submit_report_atomic(
    file: UploadFile = File(...),
    category: str = Form("road_damage"),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    village_name: Optional[str] = Form(None),
    ward_name: Optional[str] = Form(None),
    taluk_name: Optional[str] = Form("Belagavi Taluk"),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    citizen_name: Optional[str] = Form(None),
    citizen_phone: Optional[str] = Form(None),
    is_guest: Optional[bool] = Form(True),
    location_method: Optional[str] = Form("GPS_VERIFIED"),
    gps_accuracy: Optional[float] = Form(None),
    voice_transcription: Optional[str] = Form(None),
    ai_category_suggestion: Optional[str] = Form(None),
    ai_confidence: Optional[float] = Form(None),
    confirmed_latitude: Optional[float] = Form(None),
    confirmed_longitude: Optional[float] = Form(None),
    confirmed_village: Optional[str] = Form(None),
    confirmed_address: Optional[str] = Form(None),
    confirmation_method: Optional[str] = Form("CITIZEN_CONFIRMED"),
    jurisdiction_status: Optional[str] = Form("VERIFIED"),
    location_conflict_flag: Optional[bool] = Form(False),
    location_conflict_details: Optional[str] = Form(None),
    ocr_extracted_text: Optional[str] = Form(None),
    ocr_detections_json: Optional[str] = Form(None),
    landmark_candidates_json: Optional[str] = Form(None),
    photo_location_status: Optional[str] = Form(None),
    photo_location_provider: Optional[str] = Form(None),
    detected_village: Optional[str] = Form(None),
    detected_gram_panchayat: Optional[str] = Form(None),
    detected_taluk: Optional[str] = Form(None),
    detected_district: Optional[str] = Form(None),
    detected_state: Optional[str] = Form(None),
    detected_country: Optional[str] = Form("India"),
    detected_postal_code: Optional[str] = Form(None),
    google_place_id: Optional[str] = Form(None),
    geocoding_status: Optional[str] = Form(None),
    location_confirmation_status: Optional[str] = Form("UNCONFIRMED"),
    current_user: Optional[Profile] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """
    Direct atomic complaint submission endpoint:
    Accepts evidence photo and complaint details in one single HTTP request.
    Creates Issue, Submission, MediaAsset, and queues background triage atomically.
    """
    org = db.query(Organization).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Pilot organization not initialized. Run seed script first.",
        )

    # 1. Resolve or create citizen / guest profile
    guest_flag = bool(is_guest) or (current_user is None)
    if not current_user:
        clean_phone = "".join([c for c in (citizen_phone or "") if c.isdigit() or c == "+"])
        guest_email = f"guest_{clean_phone[-10:] if len(clean_phone) >= 10 else uuid.uuid4().hex[:8]}@gramaseva.internal"
        guest_profile = db.query(Profile).filter(Profile.email == guest_email).first()
        if not guest_profile:
            guest_profile = Profile(
                id=str(uuid.uuid4()),
                email=guest_email,
                password_hash="GUEST_CITIZEN_NO_LOGIN",
                full_name=citizen_name or "Guest Citizen",
                phone_number=clean_phone or None,
                preferred_locale="en",
                taluk=taluk_name or "Belagavi Taluk",
                is_active=True,
            )
            db.add(guest_profile)
            db.flush()
            ra = RoleAssignment(
                profile_id=guest_profile.id,
                role="citizen",
                is_active=True,
            )
            db.add(ra)
            db.flush()
        current_user = guest_profile

    # 2. Store photo evidence
    file_bytes = file.file.read() if hasattr(file, "file") and file.file else file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded evidence photo is empty.")

    storage_path, mime_type, size_bytes, file_hash = storage_service.store_private_media(
        file_bytes, file.filename or "evidence.jpg"
    )

    # 3. Resolve Locality Unit
    locality_unit_id = None
    target_vill = confirmed_village or village_name or detected_village or detected_gram_panchayat
    if target_vill and ("not identified" in str(target_vill).lower() or "not available" in str(target_vill).lower()):
        target_vill = None

    if target_vill:
        target_clean = str(target_vill).strip()
        loc = db.query(LocalityUnit).filter(
            (LocalityUnit.name_en.ilike(f"%{target_clean}%")) |
            (LocalityUnit.name_kn.ilike(f"%{target_clean}%"))
        ).first()
        if not loc:
            target_compact = target_clean.replace(" ", "").lower()
            all_units = db.query(LocalityUnit).filter(LocalityUnit.unit_type.in_(["gram_panchayat", "village", "ward"])).all()
            for u in all_units:
                u_compact = (u.name_en or "").replace(" ", "").lower()
                if u_compact and (u_compact in target_compact or target_compact in u_compact):
                    loc = u
                    break
                if u.name_kn and u.name_kn in target_clean:
                    loc = u
                    break
        if loc:
            locality_unit_id = loc.id

    # If still not resolved, resolve from coordinates against verified Belagavi pilot villages
    if not locality_unit_id and (confirmed_latitude or latitude) and (confirmed_longitude or longitude):
        try:
            from app.localities.router import _resolve_coordinates
            resolved = _resolve_coordinates(confirmed_latitude or latitude, confirmed_longitude or longitude, db)
            if resolved and resolved.locality_unit_id:
                locality_unit_id = resolved.locality_unit_id
                if not confirmed_village and resolved.village_name:
                    confirmed_village = resolved.village_name
        except Exception as e:
            print("Locality coordinate resolution notice:", e)

    # Check whether the resolved locality has an assigned PDO (walking up hierarchy)
    if locality_unit_id:
        has_pdo = False
        curr_id = locality_unit_id
        while curr_id:
            assigned_pdo = (
                db.query(RoleAssignment)
                .filter(
                    RoleAssignment.jurisdiction_unit_id == curr_id,
                    RoleAssignment.role.in_(["reviewer", "pdo", "village_pdo"]),
                    RoleAssignment.is_active == True,
                )
                .first()
            )
            if assigned_pdo:
                has_pdo = True
                break
            parent = db.query(LocalityUnit.parent_id).filter(LocalityUnit.id == curr_id).first()
            curr_id = parent[0] if parent else None

        # Pilot Belagavi GP verification safeguard
        if not has_pdo:
            pilot_pdo = db.query(Profile).filter(Profile.email == "pdo.peeranwadi@belagavi.gov.in").first()
            if pilot_pdo:
                has_pdo = True

        if not has_pdo:
            jurisdiction_status = "UNASSIGNED_JURISDICTION"
        else:
            jurisdiction_status = "VERIFIED"
    else:
        # Unknown locality: flag as UNASSIGNED_JURISDICTION, do NOT silently route to random PDO
        jurisdiction_status = "UNASSIGNED_JURISDICTION"
        location_conflict_flag = True
        location_conflict_details = "Location coordinates or address outside registered Gram Panchayat jurisdictions."

    effective_village = confirmed_village or village_name or detected_village
    if not effective_village and locality_unit_id:
        lu = db.query(LocalityUnit).filter(LocalityUnit.id == locality_unit_id).first()
        if lu:
            effective_village = lu.name_en

    # 4. Generate Unique Tracking ID
    tracking_id = generate_tracking_id(db)

    full_desc = description or ""
    if title and title not in full_desc:
        full_desc = f"{title}\n\n{full_desc}" if full_desc else title

    # 5. Create Issue
    issue = Issue(
        reference_number=tracking_id,
        category=category,
        status="SUBMITTED",
        priority="MEDIUM",
        organization_id=org.id,
        locality_unit_id=locality_unit_id,
        latitude=confirmed_latitude or latitude,
        longitude=confirmed_longitude or longitude,
        public_latitude=round(confirmed_latitude or latitude, 3) if (confirmed_latitude or latitude) else None,
        public_longitude=round(confirmed_longitude or longitude, 3) if (confirmed_longitude or longitude) else None,
        jurisdiction_status=jurisdiction_status or "VERIFIED",
        has_location_conflict=bool(location_conflict_flag),
        location_conflict_details=location_conflict_details,
    )
    db.add(issue)
    db.flush()

    # 6. Create Submission
    submission = Submission(
        tracking_id=tracking_id,
        reporter_id=current_user.id,
        issue_id=issue.id,
        category=category,
        description=full_desc,
        locale="en",
        original_text=full_desc,
        locality_unit_id=locality_unit_id,
        village_name=effective_village,
        ward_name=ward_name,
        taluk_name=taluk_name or "Belagavi Taluk",
        latitude=latitude,
        longitude=longitude,
        reporter_name=citizen_name or current_user.full_name,
        reporter_phone=citizen_phone or current_user.phone_number,
        is_guest=guest_flag,
        location_method=location_method or "GPS_VERIFIED",
        gps_accuracy=gps_accuracy,
        voice_transcription=voice_transcription,
        ai_category_suggestion=ai_category_suggestion,
        ai_confidence=ai_confidence,
        confirmed_latitude=confirmed_latitude or latitude,
        confirmed_longitude=confirmed_longitude or longitude,
        confirmed_village=confirmed_village or village_name,
        confirmed_address=confirmed_address,
        confirmation_method=confirmation_method or "CITIZEN_CONFIRMED",
        jurisdiction_status=jurisdiction_status or "VERIFIED",
        location_conflict_flag=bool(location_conflict_flag),
        location_conflict_details=location_conflict_details,
        ocr_extracted_text=ocr_extracted_text,
        ocr_detections_json=ocr_detections_json,
        landmark_candidates_json=landmark_candidates_json,
        photo_location_status=photo_location_status,
        photo_location_provider=photo_location_provider,
        detected_village=detected_village,
        detected_taluk=detected_taluk,
        detected_district=detected_district,
        detected_state=detected_state,
        detected_country=detected_country or "India",
        detected_postal_code=detected_postal_code,
        google_place_id=google_place_id,
        geocoding_status=geocoding_status,
        location_confirmation_status=location_confirmation_status or "UNCONFIRMED",
    )
    db.add(submission)
    db.flush()

    # Location Audit Log
    if (confirmed_latitude is not None or latitude is not None):
        try:
            audit_log = LocationAuditLog(
                id=str(uuid.uuid4()),
                submission_id=submission.id,
                issue_id=issue.id,
                actor_id=current_user.id,
                actor_role="citizen",
                field_changed="coordinates_and_jurisdiction",
                old_value=None,
                new_value=json.dumps({
                    "latitude": confirmed_latitude or latitude,
                    "longitude": confirmed_longitude or longitude,
                    "village": confirmed_village or village_name,
                    "jurisdiction_status": jurisdiction_status or "VERIFIED",
                    "location_conflict": bool(location_conflict_flag),
                }),
                reason=f"Citizen confirmed complaint location via {confirmation_method or location_method}",
            )
            db.add(audit_log)
        except Exception as e:
            print("Location audit log recording notice:", e)

    # 7. Create MediaAsset
    media = MediaAsset(
        profile_id=current_user.id,
        submission_id=submission.id,
        issue_id=issue.id,
        evidence_role="CITIZEN_BEFORE",
        storage_path=storage_path,
        file_hash=file_hash,
        mime_type=mime_type,
        file_size_bytes=size_bytes,
        is_quarantined=False,
        is_public_approved=True,
    )
    db.add(media)

    # 8. Status Event
    event = StatusEvent(
        issue_id=issue.id,
        actor_profile_id=current_user.id,
        previous_status=None,
        next_status="SUBMITTED",
        reason="Citizen submitted complaint with photographic evidence",
    )
    db.add(event)

    # 9. Queue Triage Job
    job = Job(
        task_name="triage_submission",
        payload_json=f'{{"submission_id": "{submission.id}", "issue_id": "{issue.id}"}}',
        status="QUEUED",
    )
    db.add(job)

    # 10. Notify Citizen Reporter
    try:
        from app.notifications.service import notification_service
        notification_service.send_notification(
            db=db,
            profile_id=current_user.id,
            event_type="ISSUE_SUBMITTED",
            reference_number=issue.reference_number,
            issue_id=issue.id,
            locale=submission.locale or "en",
            custom_message=f"🎉 Your complaint {issue.reference_number} has been submitted successfully to {effective_village or 'Gram Panchayat'}.",
            dedup_suffix=f"submitted-{issue.id[:8]}",
        )
    except Exception:
        pass

    db.commit()
    db.refresh(submission)
    db.refresh(issue)

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

    if isinstance(status_filter, str) and status_filter != "ALL":
        query = query.filter(Issue.status == status_filter)

    if isinstance(search, str) and search.strip():
        search_fmt = f"%{search.strip().lower()}%"
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
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
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

class CitizenClarificationRequest(BaseModel):
    message: Optional[str] = None
    clarification_response: Optional[str] = None

@router.post("/{id}/clarify")
def submit_citizen_clarification(
    id: str,
    req: CitizenClarificationRequest,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Citizen responds to PDO clarification request (Part 2, Step 3 & Part 6).
    Appends clarification response, transitions status from NEEDS_INFORMATION / AWAITING_INFORMATION
    back to UNDER_REVIEW, and alerts the PDO.
    """
    response_text = (req.message or req.clarification_response or "").strip()
    if not response_text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clarification response message cannot be empty")

    submission = db.query(Submission).filter((Submission.id == id) | (Submission.tracking_id == id)).first()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    if submission.reporter_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the reporting citizen can submit clarification for this report")

    issue = db.query(Issue).filter(Issue.id == submission.issue_id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Associated issue missing")

    prev_status = issue.status
    issue.clarification_response = response_text
    issue.status = "UNDER_REVIEW"

    # Append to description for operational transparency
    if issue.clarification_message:
        issue.resolution_review_notes = (
            f"{issue.resolution_review_notes or ''}\n[Clarification Requested]: {issue.clarification_message}\n[Citizen Response]: {response_text}"
        ).strip()

    event = StatusEvent(
        issue_id=issue.id,
        actor_profile_id=current_user.id,
        previous_status=prev_status,
        next_status="UNDER_REVIEW",
        reason=f"Citizen provided requested clarification: {response_text}",
    )
    db.add(event)
    db.commit()
    db.refresh(submission)
    db.refresh(issue)

    # In-app notification for reviewer
    try:
        from app.notifications.service import notification_service
        if issue.reviewed_by_id:
            notification_service.send_notification(
                db=db,
                profile_id=issue.reviewed_by_id,
                event_type="CLARIFICATION_PROVIDED",
                reference_number=issue.reference_number,
                issue_id=issue.id,
                locale=submission.locale,
                custom_message=f"Citizen responded to clarification for {issue.reference_number}: {req.message.strip()}",
                dedup_suffix=f"clarify-resp-{issue.id[:8]}",
            )
    except Exception:
        pass

    return build_report_response(submission, issue, db)

class FeedbackRequest(BaseModel):
    rating: int  # 1 to 5
    comment: Optional[str] = None
    is_satisfied: bool = True

@router.post("/{id}/feedback")
def submit_report_feedback(
    id: str,
    req: FeedbackRequest,
    current_user: Optional[Profile] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """Citizen submits post-repair feedback and rating (1-5 stars) for a resolved complaint."""
    if req.rating < 1 or req.rating > 5:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rating must be between 1 and 5")

    submission = db.query(Submission).filter((Submission.id == id) | (Submission.tracking_id == id)).first()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    if submission.reporter_id and current_user and submission.reporter_id != current_user.id:
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
    reporter_profile_id = current_user.id if current_user else submission.reporter_id
    existing_fb = db.query(Feedback).filter(
        Feedback.issue_id == issue.id,
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
        citizen_profile_id=reporter_profile_id,
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
    current_user: Optional[Profile] = Depends(get_optional_current_user),
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

@router.post("/check-duplicates", response_model=List[DuplicateSuggestionItem])
def check_duplicate_complaints(
    req: CheckDuplicatesRequest,
    db: Session = Depends(get_db),
):
    """
    Checks active complaints for potential duplicates based on spatial proximity,
    category match, and description similarity before citizen confirms submission.
    """
    query = (
        db.query(Issue)
        .filter(
            Issue.status.in_(["SUBMITTED", "UNDER_REVIEW", "ASSIGNED", "IN_PROGRESS", "REPAIR_REPORTED"])
        )
    )
    if req.category:
        query = query.filter(Issue.category == req.category)

    other_issues = query.all()
    suggestions: List[DuplicateSuggestionItem] = []
    max_radius = req.max_radius or 1000.0

    sub_hash = None
    if req.media_id:
        sub_media = db.query(MediaAsset).filter(MediaAsset.id == req.media_id).first()
        if sub_media and sub_media.file_hash:
            sub_hash = sub_media.file_hash

    for issue in other_issues:
        target_sub = db.query(Submission).filter(Submission.issue_id == issue.id).order_by(Submission.created_at.asc()).first()
        target_desc = target_sub.description if target_sub else ""
        target_lat = issue.latitude or (target_sub.latitude if target_sub else None)
        target_lon = issue.longitude or (target_sub.longitude if target_sub else None)

        target_media = db.query(MediaAsset).filter(MediaAsset.issue_id == issue.id).first()
        target_hash = target_media.file_hash if target_media else None

        rank_res = rank_duplicate_candidate(
            sub_lat=req.latitude,
            sub_lon=req.longitude,
            sub_desc=req.description or "",
            sub_hash=sub_hash,
            issue_lat=target_lat,
            issue_lon=target_lon,
            issue_desc=target_desc,
            issue_hash=target_hash,
            category_match=bool(req.category and issue.category == req.category),
            max_radius=max_radius,
        )

        distance = rank_res["distance_meters"]
        if req.latitude and req.longitude and target_lat and target_lon:
            if distance > max_radius and rank_res["composite_score"] < 0.35:
                continue
        elif rank_res["composite_score"] < 0.2:
            continue

        ward_name = issue.locality_unit.name_en if issue.locality_unit else "Ward Unknown"

        suggestions.append(
            DuplicateSuggestionItem(
                issue_id=issue.id,
                reference_number=issue.reference_number,
                category=issue.category,
                status=issue.status,
                distance_meters=distance,
                summary=f"{issue.category.replace('_', ' ').title()} at {ward_name}",
                ward_name=ward_name,
                composite_score=rank_res["composite_score"],
                explanation=rank_res["explanation"],
                target_media_id=target_media.id if target_media else None,
                created_at=issue.created_at,
            )
        )

    suggestions.sort(key=lambda s: s.composite_score, reverse=True)
    return suggestions[:5]

@router.get("/{id}/duplicate-suggestions", response_model=List[DuplicateSuggestionItem])
def get_report_duplicate_suggestions(
    id: str,
    db: Session = Depends(get_db),
):
    """
    Retrieves transparent duplicate suggestions for a report draft or submitted complaint.
    Enables citizen self-serve duplicate awareness during reporting.
    Never auto-merges (README Section 4.3).
    """
    submission = db.query(Submission).filter((Submission.id == id) | (Submission.tracking_id == id)).first()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    sub_media = db.query(MediaAsset).filter(MediaAsset.submission_id == submission.id).first()
    sub_hash = sub_media.file_hash if sub_media else None

    # Search existing issues with matching category
    query = (
        db.query(Issue)
        .filter(
            Issue.id != submission.issue_id,
            Issue.category == submission.category,
            Issue.status.in_(["SUBMITTED", "UNDER_REVIEW", "ASSIGNED", "IN_PROGRESS", "REPAIR_REPORTED"]),
        )
    )

    other_issues = query.all()
    suggestions: List[DuplicateSuggestionItem] = []

    for issue in other_issues:
        target_sub = db.query(Submission).filter(Submission.issue_id == issue.id).order_by(Submission.created_at.asc()).first()
        target_desc = target_sub.description if target_sub else ""
        target_lat = issue.latitude or (target_sub.latitude if target_sub else None)
        target_lon = issue.longitude or (target_sub.longitude if target_sub else None)

        target_media = db.query(MediaAsset).filter(MediaAsset.issue_id == issue.id).first()
        target_hash = target_media.file_hash if target_media else None

        rank_res = rank_duplicate_candidate(
            sub_lat=submission.latitude,
            sub_lon=submission.longitude,
            sub_desc=submission.description,
            sub_hash=sub_hash,
            issue_lat=target_lat,
            issue_lon=target_lon,
            issue_desc=target_desc,
            issue_hash=target_hash,
            category_match=True,
            max_radius=500.0,
        )

        distance = rank_res["distance_meters"]
        exact_sha_match = bool(sub_hash and target_hash and sub_hash == target_hash)

        # Only suggest if within 500m or strong candidate
        if distance > 500 and not exact_sha_match:
            continue

        ward_name = issue.locality_unit.name_en if issue.locality_unit else "Ward Unknown"

        suggestions.append(
            DuplicateSuggestionItem(
                issue_id=issue.id,
                reference_number=issue.reference_number,
                category=issue.category,
                status=issue.status,
                distance_meters=distance,
                summary=f"{issue.category} at {ward_name}",
                ward_name=ward_name,
                composite_score=rank_res["composite_score"],
                explanation=rank_res["explanation"],
                target_media_id=target_media.id if target_media else None,
                created_at=issue.created_at,
            )
        )

    suggestions.sort(key=lambda s: s.composite_score, reverse=True)
    return suggestions

@router.post("/sync", response_model=SyncReportResponse)
def sync_offline_drafts(
    items: List[OfflineDraftSyncItem],
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Idempotent sync for citizen reports drafted while offline (README Section 4.1, 8, Phase 8).
    Ensures that retries with the same idempotency key never duplicate submissions or issues.
    """
    synced_reports = []
    default_org = db.query(Organization).first()

    for item in items:
        # Check idempotency: match tracking_id with idempotency_key or existing identical draft
        existing_sub = (
            db.query(Submission)
            .filter(
                (Submission.tracking_id == item.idempotency_key)
                | (
                    (Submission.reporter_id == current_user.id)
                    & (Submission.description == item.description)
                    & (Submission.category == item.category)
                )
            )
            .first()
        )

        if existing_sub:
            issue = db.query(Issue).filter(Issue.id == existing_sub.issue_id).first() if existing_sub.issue_id else None
            synced_reports.append(build_report_response(existing_sub, issue, db))
            continue

        # Create new issue & submission atomically
        tracking_id = generate_tracking_id(db)
        unique_ref = f"{tracking_id}"

        issue = Issue(
            reference_number=unique_ref,
            category=item.category,
            status="SUBMITTED",
            priority="MEDIUM",
            organization_id=default_org.id if default_org else "default-org",
            locality_unit_id=item.locality_unit_id,
            latitude=item.latitude,
            longitude=item.longitude,
            public_latitude=round(item.latitude, 3) if item.latitude else None,
            public_longitude=round(item.longitude, 3) if item.longitude else None,
        )
        db.add(issue)
        db.flush()

        sub = Submission(
            tracking_id=tracking_id,
            reporter_id=current_user.id,
            issue_id=issue.id,
            category=item.category,
            description=item.description,
            locale=item.locale or "en",
            original_text=item.description,
            locality_unit_id=item.locality_unit_id,
            village_name=item.village_name,
            ward_name=item.ward_name,
            latitude=item.latitude,
            longitude=item.longitude,
        )
        db.add(sub)

        event = StatusEvent(
            issue_id=issue.id,
            actor_profile_id=current_user.id,
            previous_status=None,
            next_status="SUBMITTED",
            reason="Submitted via offline sync queue",
        )
        db.add(event)
        db.commit()

        synced_reports.append(build_report_response(sub, issue, db))

    return SyncReportResponse(synced_count=len(synced_reports), items=synced_reports)

