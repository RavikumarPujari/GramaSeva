import math
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
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
    Uses category and proximity matching. Never auto-merges (README Section 4.3).
    """
    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

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
        distance = 0.0
        if sub.latitude and sub.longitude and issue.latitude and issue.longitude:
            distance = calculate_haversine_distance(
                sub.latitude, sub.longitude, issue.latitude, issue.longitude
            )
            # Within 300 meters is a strong candidate
            if distance > 1000:
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
                created_at=issue.created_at,
            )
        )

    # Sort by closest distance
    candidates.sort(key=lambda c: c.distance_meters)
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

    return {
        "status": "success",
        "issue_id": issue.id,
        "new_status": issue.status,
        "resolved_at": issue.resolved_at,
    }
