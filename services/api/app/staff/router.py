import math
import sys
import os
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from workers.adapters.duplicate.similarity import rank_duplicate_candidate, compute_haversine_distance
from workers.adapters.evidence_assistance.adapter import evidence_assistance_adapter
from app.storage.service import storage_service
from app.models.users import Profile, RoleAssignment
from app.models.localities import LocalityUnit, Department
from app.models.issues import (
    Issue,
    Submission,
    MediaAsset,
    Assignment,
    RepairReview,
    StatusEvent,
    AuditLog,
    DuplicateCandidate,
    Asset,
    RecurrenceCandidate,
)
from app.auth.dependencies import (
    get_current_user,
    require_roles,
    verify_jurisdiction_scope,
    verify_separation_of_duty,
)
from app.staff.schemas import (
    StaffInboxItem,
    TriageActionRequest,
    DuplicateCandidateItem,
    DuplicateDecisionRequest,
    ResolutionQueueItem,
    ResolutionReviewRequest,
)

router = APIRouter(prefix="/staff", tags=["Staff Triage & Verification"])

def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two coordinates in meters."""
    R = 6371000  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 1)

@router.get("/inbox", response_model=List[StaffInboxItem])
def get_reviewer_inbox(
    status_filter: Optional[str] = Query(None),
    current_reviewer: Profile = Depends(require_roles("reviewer", "admin")),
    db: Session = Depends(get_db),
):
    """
    Returns submitted issues and complaints awaiting triage within the reviewer's jurisdiction.
    Enforces server-side jurisdiction scoping.
    """
    query = (
        db.query(Submission, Issue)
        .join(Issue, Submission.issue_id == Issue.id)
    )

    if status_filter:
        query = query.filter(Issue.status == status_filter)
    else:
        query = query.filter(Issue.status.in_(["SUBMITTED", "UNDER_REVIEW", "NEEDS_INFORMATION"]))

    submissions_and_issues = query.order_by(Submission.created_at.desc()).all()
    results: List[StaffInboxItem] = []

    for sub, issue in submissions_and_issues:
        # Jurisdiction check
        if not verify_jurisdiction_scope(db, current_reviewer.id, issue.locality_unit_id):
            continue

        photos_count = (
            db.query(MediaAsset)
            .filter(MediaAsset.submission_id == sub.id)
            .count()
        )

        results.append(
            StaffInboxItem(
                submission_id=sub.id,
                tracking_id=sub.tracking_id,
                issue_id=issue.id,
                reference_number=issue.reference_number,
                category=issue.category,
                description=sub.description,
                status=issue.status,
                priority=issue.priority,
                village_name=sub.village_name,
                ward_name=sub.ward_name,
                locality_unit_id=issue.locality_unit_id,
                submitted_at=sub.created_at,
                photos_count=photos_count,
            )
        )

    return results

@router.post("/issues/{issue_id}/triage")
def triage_issue(
    issue_id: str,
    req: TriageActionRequest,
    current_reviewer: Profile = Depends(require_roles("reviewer", "admin")),
    db: Session = Depends(get_db),
):
    """
    Triage complaint:
    - Reviewer can correct category or ward with audit reason
    - Sets official priority
    - Routes to configured department and assigns field worker
    """
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    # Enforce jurisdiction
    if not verify_jurisdiction_scope(db, current_reviewer.id, issue.locality_unit_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff jurisdiction violation: Issue locality is outside your assigned jurisdiction",
        )

    prev_status = issue.status

    # Category correction with audit note
    if req.corrected_category and req.corrected_category != issue.category:
        event = StatusEvent(
            issue_id=issue.id,
            actor_profile_id=current_reviewer.id,
            previous_status=issue.status,
            next_status=issue.status,
            reason=f"Category corrected from {issue.category} to {req.corrected_category}. Note: {req.audit_reason}",
        )
        db.add(event)
        issue.category = req.corrected_category

    # Ward correction
    if req.corrected_ward_id and req.corrected_ward_id != issue.locality_unit_id:
        ward_unit = db.query(LocalityUnit).filter(LocalityUnit.id == req.corrected_ward_id).first()
        if ward_unit:
            event = StatusEvent(
                issue_id=issue.id,
                actor_profile_id=current_reviewer.id,
                previous_status=issue.status,
                next_status=issue.status,
                reason=f"Ward assigned/corrected to {ward_unit.name_en}. Note: {req.audit_reason}",
            )
            db.add(event)
            issue.locality_unit_id = ward_unit.id

    # Department and priority
    issue.priority = req.priority
    issue.department_id = req.department_id

    # Assignment to worker
    if req.assigned_worker_id:
        worker = db.query(Profile).filter(Profile.id == req.assigned_worker_id).first()
        if not worker:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigned worker profile not found")

        issue.assigned_worker_id = worker.id
        issue.status = "ASSIGNED"

        assignment = Assignment(
            issue_id=issue.id,
            department_id=req.department_id,
            worker_profile_id=worker.id,
            assigned_by_id=current_reviewer.id,
            instructions=req.instructions,
            status="ASSIGNED",
        )
        db.add(assignment)

        status_event = StatusEvent(
            issue_id=issue.id,
            actor_profile_id=current_reviewer.id,
            previous_status=prev_status,
            next_status="ASSIGNED",
            reason=f"Assigned to worker {worker.full_name}. Priority: {req.priority}. Reason: {req.audit_reason}",
        )
        db.add(status_event)
    else:
        issue.status = "UNDER_REVIEW"
        status_event = StatusEvent(
            issue_id=issue.id,
            actor_profile_id=current_reviewer.id,
            previous_status=prev_status,
            next_status="UNDER_REVIEW",
            reason=f"Triaged and verified by reviewer. Priority: {req.priority}. Reason: {req.audit_reason}",
        )
        db.add(status_event)

    db.commit()
    db.refresh(issue)

    # In-app notifications for reporters
    if issue.status == "ASSIGNED":
        from app.notifications.service import notification_service
        subs = db.query(Submission).filter(Submission.issue_id == issue.id).all()
        for s in subs:
            notification_service.send_notification(
                db=db,
                profile_id=s.reporter_id,
                event_type="ISSUE_ASSIGNED",
                reference_number=issue.reference_number,
                issue_id=issue.id,
                locale=s.locale,
                dedup_suffix=f"assigned-{issue.priority}",
            )

    return {
        "status": "success",
        "issue_id": issue.id,
        "new_status": issue.status,
        "priority": issue.priority,
        "assigned_worker_id": issue.assigned_worker_id,
    }

@router.get("/duplicate-candidates", response_model=List[DuplicateCandidateItem])
def get_duplicate_candidates(
    submission_id: str,
    current_reviewer: Profile = Depends(require_roles("reviewer", "admin")),
    db: Session = Depends(get_db),
):
    """
    Searches for nearby physical issues that may be duplicate reports.
    Uses multi-signal ranking (spatial, text, and visual similarity).
    Never auto-merges: requires explicit human decision (README Section 4.3).
    """
    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

    # Get submission media hash if available
    sub_media = db.query(MediaAsset).filter(MediaAsset.submission_id == sub.id).first()
    sub_hash = sub_media.file_hash if sub_media else None

    candidates: List[DuplicateCandidateItem] = []
    
    # Query other issues with matching category
    query = (
        db.query(Issue)
        .filter(
            Issue.id != sub.issue_id,
            Issue.category == sub.category,
            Issue.status.in_(["SUBMITTED", "UNDER_REVIEW", "ASSIGNED", "IN_PROGRESS", "REPAIR_REPORTED"]),
        )
    )

    other_issues = query.all()

    for issue in other_issues:
        # Get target issue primary submission & media
        target_sub = db.query(Submission).filter(Submission.issue_id == issue.id).order_by(Submission.created_at.asc()).first()
        target_desc = target_sub.description if target_sub else ""
        target_lat = issue.latitude or (target_sub.latitude if target_sub else None)
        target_lon = issue.longitude or (target_sub.longitude if target_sub else None)

        target_media = db.query(MediaAsset).filter(MediaAsset.issue_id == issue.id).first()
        target_hash = target_media.file_hash if target_media else None

        # Check for exact photo re-upload match
        exact_sha_match = bool(sub_hash and target_hash and sub_hash == target_hash)

        rank_res = rank_duplicate_candidate(
            sub_lat=sub.latitude,
            sub_lon=sub.longitude,
            sub_desc=sub.description,
            sub_hash=sub_hash,
            issue_lat=target_lat,
            issue_lon=target_lon,
            issue_desc=target_desc,
            issue_hash=target_hash,
            category_match=True,
            max_radius=500.0,
        )

        distance = rank_res["distance_meters"]
        # Skip if beyond 1000 meters unless exact image match
        if distance > 1000 and not exact_sha_match:
            continue

        # Locality unit name
        ward_name = issue.locality_unit.name_en if issue.locality_unit else "Ward Unknown"

        candidates.append(
            DuplicateCandidateItem(
                issue_id=issue.id,
                reference_number=issue.reference_number,
                category=issue.category,
                status=issue.status,
                distance_meters=distance,
                summary=f"{issue.category} at {ward_name}",
                ward_name=ward_name,
                spatial_score=rank_res["spatial_score"],
                text_score=rank_res["text_score"],
                visual_score=rank_res["visual_score"],
                composite_score=rank_res["composite_score"],
                explanation=rank_res["explanation"],
                is_strong_candidate=rank_res["is_strong_candidate"],
                created_at=issue.created_at,
            )
        )

    # Sort by highest composite score first
    candidates.sort(key=lambda c: (c.composite_score or 0.0), reverse=True)
    return candidates

@router.post("/duplicate-candidates/decide")
def decide_duplicate(
    req: DuplicateDecisionRequest,
    current_reviewer: Profile = Depends(require_roles("reviewer", "admin")),
    db: Session = Depends(get_db),
):
    """
    Authority reviewer decides whether to link submission to an existing issue.
    Preserves both citizen submissions and all original evidence (Section 1.2).
    """
    sub = db.query(Submission).filter(Submission.id == req.submission_id).first()
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

    target_issue = db.query(Issue).filter(Issue.id == req.target_issue_id).first()
    if not target_issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target issue not found")

    if req.decision == "LINK_DUPLICATE":
        old_issue_id = sub.issue_id
        # Link submission to shared physical issue
        sub.issue_id = target_issue.id

        # Also link associated media assets to target issue
        media_assets = db.query(MediaAsset).filter(MediaAsset.submission_id == sub.id).all()
        for m in media_assets:
            m.issue_id = target_issue.id

        cand = DuplicateCandidate(
            submission_id=sub.id,
            target_issue_id=target_issue.id,
            detection_method="reviewer_decision",
            decision="CONFIRMED_DUPLICATE",
            adjudicated_by_id=current_reviewer.id,
            notes=req.reason,
        )
        db.add(cand)

        event = StatusEvent(
            issue_id=target_issue.id,
            actor_profile_id=current_reviewer.id,
            previous_status=target_issue.status,
            next_status=target_issue.status,
            reason=f"Citizen submission {sub.tracking_id} linked to shared issue {target_issue.reference_number}. Reason: {req.reason}",
        )
        db.add(event)

        # If previous issue has zero other submissions, mark it superseded
        if old_issue_id and old_issue_id != target_issue.id:
            other_subs = db.query(Submission).filter(Submission.issue_id == old_issue_id).count()
            if other_subs == 0:
                old_issue = db.query(Issue).filter(Issue.id == old_issue_id).first()
                if old_issue:
                    old_issue.status = "SUPERSEDED"

        db.commit()
        return {
            "status": "linked",
            "decision": "CONFIRMED_DUPLICATE",
            "submission_tracking_id": sub.tracking_id,
            "linked_to_issue": target_issue.reference_number,
        }

    else:
        # Keep separate issues
        cand = DuplicateCandidate(
            submission_id=sub.id,
            target_issue_id=target_issue.id,
            detection_method="reviewer_decision",
            decision="REJECTED_DIFFERENT",
            adjudicated_by_id=current_reviewer.id,
            notes=req.reason,
        )
        db.add(cand)
        db.commit()
        return {
            "status": "kept_separate",
            "decision": "REJECTED_DIFFERENT",
            "submission_tracking_id": sub.tracking_id,
        }

@router.get("/resolution-queue", response_model=List[ResolutionQueueItem])
def get_resolution_queue(
    current_reviewer: Profile = Depends(require_roles("reviewer", "admin")),
    db: Session = Depends(get_db),
):
    """
    Lists all issues in REPAIR_REPORTED status awaiting independent review.
    Side-by-side before and after photo references provided.
    """
    issues = (
        db.query(Issue)
        .filter(Issue.status == "REPAIR_REPORTED")
        .order_by(Issue.updated_at.desc())
        .all()
    )

    results: List[ResolutionQueueItem] = []
    for issue in issues:
        if not verify_jurisdiction_scope(db, current_reviewer.id, issue.locality_unit_id):
            continue

        worker_name = issue.assigned_worker.full_name if issue.assigned_worker else "Unknown Worker"

        before_media = (
            db.query(MediaAsset.id)
            .filter(MediaAsset.issue_id == issue.id, MediaAsset.evidence_role == "CITIZEN_BEFORE")
            .all()
        )
        after_media = (
            db.query(MediaAsset.id)
            .filter(MediaAsset.issue_id == issue.id, MediaAsset.evidence_role == "WORKER_AFTER")
            .all()
        )

        results.append(
            ResolutionQueueItem(
                issue_id=issue.id,
                reference_number=issue.reference_number,
                category=issue.category,
                village_name=issue.locality_unit.name_en if issue.locality_unit else None,
                ward_name=issue.locality_unit.name_en if issue.locality_unit else "Ward Unknown",
                assigned_worker_name=worker_name,
                assigned_worker_id=issue.assigned_worker_id,
                reported_repair_at=issue.updated_at,
                repair_notes=issue.resolution_review_notes,
                before_photo_ids=[m[0] for m in before_media],
                after_photo_ids=[m[0] for m in after_media],
            )
        )

    return results

@router.post("/issues/{issue_id}/resolution")
def review_resolution(
    issue_id: str,
    req: ResolutionReviewRequest,
    current_reviewer: Profile = Depends(require_roles("reviewer", "admin")),
    db: Session = Depends(get_db),
):
    """
    Independent resolution review:
    Enforces separation-of-duty: worker cannot approve their own repair.
    Approves or requests better evidence.
    """
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    # Enforce jurisdiction
    if not verify_jurisdiction_scope(db, current_reviewer.id, issue.locality_unit_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff jurisdiction violation: Locality is outside your assigned jurisdiction",
        )

    # Enforce separation of duty (Rule Section 2.2 & 17.4)
    if not verify_separation_of_duty(issue.assigned_worker_id, current_reviewer.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Separation-of-Duty Violation: You cannot approve a repair resolution for work you performed as the assigned field worker.",
        )

    prev_status = issue.status

    if req.decision == "APPROVE":
        issue.status = "RESOLVED"
        issue.resolved_at = datetime.now(timezone.utc)
        issue.reviewed_by_id = current_reviewer.id
        issue.resolution_review_notes = req.explanation

        review = RepairReview(
            issue_id=issue.id,
            reviewer_profile_id=current_reviewer.id,
            decision="APPROVED",
            explanation=req.explanation,
        )
        db.add(review)

        event = StatusEvent(
            issue_id=issue.id,
            actor_profile_id=current_reviewer.id,
            previous_status=prev_status,
            next_status="RESOLVED",
            reason=f"Repair independently verified and approved by {current_reviewer.full_name}. Note: {req.explanation}",
        )
        db.add(event)

    else:
        # Request better evidence or reopen
        issue.status = "IN_PROGRESS"
        issue.resolution_review_notes = req.explanation

        review = RepairReview(
            issue_id=issue.id,
            reviewer_profile_id=current_reviewer.id,
            decision="EVIDENCE_REQUESTED",
            explanation=req.explanation,
        )
        db.add(review)

        event = StatusEvent(
            issue_id=issue.id,
            actor_profile_id=current_reviewer.id,
            previous_status=prev_status,
            next_status="IN_PROGRESS",
            reason=f"Better repair evidence requested by reviewer: {req.explanation}",
        )
        db.add(event)

    db.commit()
    db.refresh(issue)

    if req.decision == "APPROVED":
        from app.notifications.service import notification_service
        subs = db.query(Submission).filter(Submission.issue_id == issue.id).all()
        for s in subs:
            notification_service.send_notification(
                db=db,
                profile_id=s.reporter_id,
                event_type="RESOLUTION_APPROVED",
                reference_number=issue.reference_number,
                issue_id=issue.id,
                locale=s.locale,
                dedup_suffix=f"resolved-{issue.id[:8]}",
            )

    return {
        "status": "success",
        "issue_id": issue.id,
        "new_status": issue.status,
        "resolved_at": issue.resolved_at,
    }

class RedactMediaRequest(BaseModel):
    reason: str
    redaction_type: str = "sensitive_blur"  # face, license_plate, private_property

@router.post("/media/{media_id}/approve-public")
def approve_media_for_public(
    media_id: str,
    current_reviewer: Profile = Depends(require_roles("reviewer", "admin")),
    db: Session = Depends(get_db),
):
    """Staff moderator approves a photo asset for public viewing after verifying no private info is leaked."""
    media = db.query(MediaAsset).filter(MediaAsset.id == media_id).first()
    if not media:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media asset not found")

    media.is_public_approved = True
    media.is_quarantined = False

    audit = AuditLog(
        actor_profile_id=current_reviewer.id,
        action="APPROVE_PUBLIC_MEDIA",
        target_type="MEDIA_ASSET",
        target_id=media.id,
        details_json=f'{{"approved_by": "{current_reviewer.full_name}", "evidence_role": "{media.evidence_role}"}}',
    )
    db.add(audit)
    db.commit()

    return {"status": "success", "media_id": media.id, "is_public_approved": True}

@router.post("/media/{media_id}/quarantine")
def quarantine_media(
    media_id: str,
    reason: str = Query("Contains private or non-compliant content"),
    current_reviewer: Profile = Depends(require_roles("reviewer", "admin")),
    db: Session = Depends(get_db),
):
    """Staff moderator quarantines media, removing it from all public and standard views."""
    media = db.query(MediaAsset).filter(MediaAsset.id == media_id).first()
    if not media:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media asset not found")

    media.is_public_approved = False
    media.is_quarantined = True

    audit = AuditLog(
        actor_profile_id=current_reviewer.id,
        action="QUARANTINE_MEDIA",
        target_type="MEDIA_ASSET",
        target_id=media.id,
        details_json=f'{{"reason": "{reason}", "actor": "{current_reviewer.full_name}"}}',
    )
    db.add(audit)
    db.commit()

    return {"status": "quarantined", "media_id": media.id, "is_quarantined": True}

@router.post("/media/{media_id}/redact")
def redact_media(
    media_id: str,
    req: RedactMediaRequest,
    current_reviewer: Profile = Depends(require_roles("reviewer", "admin")),
    db: Session = Depends(get_db),
):
    """Records media redaction (face, license plate, private property) and marks it safe for public display."""
    media = db.query(MediaAsset).filter(MediaAsset.id == media_id).first()
    if not media:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media asset not found")

    media.is_public_approved = True
    media.is_quarantined = False

    audit = AuditLog(
        actor_profile_id=current_reviewer.id,
        action="REDACT_MEDIA",
        target_type="MEDIA_ASSET",
        target_id=media.id,
        details_json=f'{{"redaction_type": "{req.redaction_type}", "reason": "{req.reason}", "actor": "{current_reviewer.full_name}"}}',
    )
    db.add(audit)
    db.commit()

    return {"status": "redacted_and_approved", "media_id": media.id, "is_public_approved": True}

# --- Phase 8 Advanced Endpoints: Evidence Assistance, Asset Linking & Recurrence ---

class EvidenceAssistanceResponse(BaseModel):
    issue_id: str
    visible_change: bool
    possible_mismatch: bool
    insufficient_evidence: bool
    visual_consistency_score: float
    difference_summary: str
    advisory_decision_suggestion: str
    governance_notice: str
    requires_independent_human_review: bool = True

class LinkAssetRequest(BaseModel):
    asset_id: str

class RecurrenceCandidateItem(BaseModel):
    candidate_id: str
    new_issue_id: str
    new_issue_ref: str
    prior_issue_id: str
    prior_issue_ref: str
    category: str
    distance_meters: float
    days_since_resolution: int
    decision: str
    notes: Optional[str] = None
    created_at: datetime

class RecurrenceDecisionRequest(BaseModel):
    decision: str  # CONFIRMED_RECURRENCE or REJECTED_UNRELATED
    notes: Optional[str] = None
    priority_boost: Optional[str] = None

@router.get("/issues/{id}/evidence-assistance", response_model=EvidenceAssistanceResponse)
def get_repair_evidence_assistance(
    id: str,
    current_reviewer: Profile = Depends(require_roles("reviewer", "admin")),
    db: Session = Depends(get_db),
):
    """
    Compares citizen pre-repair evidence vs worker repair proof (README Section 7.8, Phase 8).
    Strict Rule: AI cannot approve repair or determine safety. Reviewer must independently decide.
    """
    issue = db.query(Issue).filter(Issue.id == id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    before_media = (
        db.query(MediaAsset)
        .filter(MediaAsset.issue_id == issue.id, MediaAsset.evidence_role == "CITIZEN_BEFORE")
        .first()
    )
    after_media = (
        db.query(MediaAsset)
        .filter(MediaAsset.issue_id == issue.id, MediaAsset.evidence_role == "WORKER_AFTER")
        .first()
    )

    if not before_media or not after_media:
        return EvidenceAssistanceResponse(
            issue_id=issue.id,
            visible_change=False,
            possible_mismatch=False,
            insufficient_evidence=True,
            visual_consistency_score=0.0,
            difference_summary="Insufficient evidence: Either before or after photo is missing for automated comparison.",
            advisory_decision_suggestion="REQUEST_EVIDENCE",
            governance_notice="AI is advisory only. Authorized reviewer must independently verify repairs.",
            requires_independent_human_review=True,
        )

    before_path = storage_service.get_absolute_path(before_media.storage_path)
    after_path = storage_service.get_absolute_path(after_media.storage_path)

    res = evidence_assistance_adapter.analyze_evidence_pair(
        before_image=before_path,
        after_image=after_path,
        before_hash=before_media.file_hash,
        after_hash=after_media.file_hash,
    )

    return EvidenceAssistanceResponse(
        issue_id=issue.id,
        visible_change=res["visible_change"],
        possible_mismatch=res["possible_mismatch"],
        insufficient_evidence=res["insufficient_evidence"],
        visual_consistency_score=res.get("visual_consistency_score", 0.0),
        difference_summary=res["difference_summary"],
        advisory_decision_suggestion=res["advisory_decision_suggestion"],
        governance_notice=res["governance_notice"],
        requires_independent_human_review=True,
    )

@router.post("/issues/{id}/link-asset")
def link_issue_to_asset(
    id: str,
    req: LinkAssetRequest,
    current_reviewer: Profile = Depends(require_roles("reviewer", "admin")),
    db: Session = Depends(get_db),
):
    """Links verified public infrastructure asset to this issue (README Section 5.2)."""
    issue = db.query(Issue).filter(Issue.id == id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    asset = db.query(Asset).filter(Asset.id == req.asset_id).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    issue.asset_id = asset.id
    db.commit()

    return {
        "status": "linked",
        "issue_id": issue.id,
        "asset_id": asset.id,
        "asset_code": asset.official_code,
        "asset_name": asset.name_en,
    }

@router.get("/recurrence-candidates", response_model=List[RecurrenceCandidateItem])
def get_recurrence_candidates(
    current_reviewer: Profile = Depends(require_roles("reviewer", "admin")),
    db: Session = Depends(get_db),
):
    """
    Lists flagged recurrence candidates where an issue matches a previously resolved defect nearby.
    Reviewers confirm or reject the relationship (README Section 4.4, Phase 8).
    """
    candidates = (
        db.query(RecurrenceCandidate)
        .filter(RecurrenceCandidate.decision == "PENDING")
        .order_by(RecurrenceCandidate.created_at.desc())
        .all()
    )

    out = []
    for c in candidates:
        new_i = db.query(Issue).filter(Issue.id == c.new_issue_id).first()
        prior_i = db.query(Issue).filter(Issue.id == c.prior_issue_id).first()
        if new_i and prior_i:
            out.append(
                RecurrenceCandidateItem(
                    candidate_id=c.id,
                    new_issue_id=c.new_issue_id,
                    new_issue_ref=new_i.reference_number,
                    prior_issue_id=c.prior_issue_id,
                    prior_issue_ref=prior_i.reference_number,
                    category=new_i.category,
                    distance_meters=c.distance_meters,
                    days_since_resolution=c.days_since_resolution,
                    decision=c.decision,
                    notes=c.notes,
                    created_at=c.created_at,
                )
            )
    return out

@router.post("/recurrence-candidates/{candidate_id}/decide")
def decide_recurrence_candidate(
    candidate_id: str,
    req: RecurrenceDecisionRequest,
    current_reviewer: Profile = Depends(require_roles("reviewer", "admin")),
    db: Session = Depends(get_db),
):
    """Human reviewer confirms or rejects recurrence relationship and optionally escalates priority."""
    if req.decision not in ("CONFIRMED_RECURRENCE", "REJECTED_UNRELATED"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decision must be CONFIRMED_RECURRENCE or REJECTED_UNRELATED",
        )

    cand = db.query(RecurrenceCandidate).filter(RecurrenceCandidate.id == candidate_id).first()
    if not cand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurrence candidate not found")

    cand.decision = req.decision
    cand.adjudicated_by_id = current_reviewer.id
    cand.adjudicated_at = datetime.now(timezone.utc)
    if req.notes:
        cand.notes = f"{cand.notes or ''} | Reviewer: {req.notes}".strip()

    new_issue = db.query(Issue).filter(Issue.id == cand.new_issue_id).first()
    if new_issue and req.decision == "CONFIRMED_RECURRENCE":
        new_issue.is_recurrence = True
        new_issue.prior_resolved_issue_id = cand.prior_issue_id
        if req.priority_boost:
            new_issue.priority = req.priority_boost

    db.commit()

    return {
        "status": "adjudicated",
        "candidate_id": cand.id,
        "decision": cand.decision,
        "is_recurrence": new_issue.is_recurrence if new_issue else False,
        "new_priority": new_issue.priority if new_issue else None,
    }


