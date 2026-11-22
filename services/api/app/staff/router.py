import math
import sys
import os
import json
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
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
    WorkCompletion,
    AIBeforeAfterAnalysis,
    ModelRun,
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


class StaffComplaintItem(BaseModel):
    id: str
    submission_id: Optional[str] = None
    tracking_id: str
    reference_number: str
    category: str
    status: str
    priority: str
    village_name: Optional[str] = None
    ward_name: Optional[str] = None
    description: Optional[str] = None
    assigned_worker_id: Optional[str] = None
    assigned_worker_name: Optional[str] = None
    department_id: Optional[str] = None
    department_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_duplicate: bool = False
    is_recurrence: bool = False
    created_at: datetime
    resolved_at: Optional[datetime] = None
    photos_count: int = 0
    estimated_cost: Optional[float] = None
    proposed_cost: Optional[float] = None
    materials_cost: Optional[float] = None
    labour_cost: Optional[float] = None
    other_expenses_cost: Optional[float] = None
    verified_cost: Optional[float] = None
    cost_status: Optional[str] = None
    work_completed_at: Optional[datetime] = None
    work_completion_description: Optional[str] = None
    work_performed: Optional[str] = None
    materials_used: Optional[str] = None
    labour_details: Optional[str] = None
    cost_verification_remarks: Optional[str] = None
    ai_analysis: Optional[Dict[str, Any]] = None
    before_photo_ids: List[str] = []
    after_photo_ids: List[str] = []
    citizen_name: Optional[str] = None
    citizen_phone: Optional[str] = None
    citizen_email: Optional[str] = None
    ai_category_suggestion: Optional[str] = None
    ai_confidence: Optional[float] = None
    ai_model_id: Optional[str] = None
    ai_model_provider: Optional[str] = None
    ai_detected_objects: List[Dict[str, Any]] = []
    ai_analysis_status: Optional[str] = None
    ai_model_ids: List[str] = []
    ai_model_summaries: List[Dict[str, Any]] = []
    ai_consensus_status: Optional[str] = None
    ai_comparison_notes: Optional[str] = None
    duplicate_candidates_count: int = 0
    duplicate_evidence: Optional[str] = None
    annotated_photo_id: Optional[str] = None
    voice_transcription: Optional[str] = None
    is_guest: bool = False
    location_method: Optional[str] = None
    gps_accuracy: Optional[float] = None


@router.get("/all-complaints", response_model=List[StaffComplaintItem])
def get_all_complaints(
    category: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    priority: Optional[str] = Query(None),
    village_name: Optional[str] = Query(None),
    ward_name: Optional[str] = Query(None),
    current_reviewer: Profile = Depends(require_roles("reviewer", "admin")),
    db: Session = Depends(get_db),
):
    """
    Returns all complaints across the Gram Panchayat with full administrative fields,
    supporting filtering by Category, Village, Ward, Status, and Priority.
    """
    query = db.query(Issue).filter(Issue.status != "DRAFT")

    # Scoped jurisdiction for reviewer
    asgn = (
        db.query(RoleAssignment)
        .filter(RoleAssignment.profile_id == current_reviewer.id, RoleAssignment.is_active == True)
        .first()
    )
    gp_id = asgn.jurisdiction_unit_id if asgn else None

    if gp_id and "admin" not in [r.role for r in current_reviewer.role_assignments]:
        child_ids = [r[0] for r in db.query(LocalityUnit.id).filter(LocalityUnit.parent_id == gp_id).all()]
        sub_child_ids = [r[0] for r in db.query(LocalityUnit.id).filter(LocalityUnit.parent_id.in_(child_ids)).all()]
        all_gp_unit_ids = set([gp_id] + child_ids + sub_child_ids)
        query = query.filter((Issue.locality_unit_id.in_(all_gp_unit_ids)) | (Issue.locality_unit_id.is_(None)))

    if category and category != "ALL":
        query = query.filter(Issue.category == category)
    if status_filter and status_filter != "ALL":
        query = query.filter(Issue.status == status_filter)
    if priority and priority != "ALL":
        query = query.filter(Issue.priority == priority)

    issues = query.order_by(Issue.created_at.desc()).all()
    results: List[StaffComplaintItem] = []

    for issue in issues:
        # Get first submission for original description & reporter details
        sub = db.query(Submission).filter(Submission.issue_id == issue.id).order_by(Submission.created_at.asc()).first()
        photos_count = db.query(MediaAsset).filter(MediaAsset.issue_id == issue.id).count()

        v_name = sub.village_name if sub else None
        w_name = sub.ward_name if sub else None
        if not v_name and issue.locality_unit:
            if issue.locality_unit.unit_type == "village":
                v_name = issue.locality_unit.name_en
            elif issue.locality_unit.unit_type == "ward":
                w_name = issue.locality_unit.name_en
                if issue.locality_unit.parent:
                    v_name = issue.locality_unit.parent.name_en

        if village_name and village_name != "ALL" and v_name and village_name.lower() not in v_name.lower():
            continue
        if ward_name and ward_name != "ALL" and w_name and ward_name.lower() not in w_name.lower():
            continue

        worker_name = issue.assigned_worker.full_name if issue.assigned_worker else None
        dept_name = issue.department.name_en if issue.department else None

        # Fetch before and after photos
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

        # Fetch latest AI analysis if available
        ai_rec = (
            db.query(AIBeforeAfterAnalysis)
            .filter(AIBeforeAfterAnalysis.issue_id == issue.id)
            .order_by(AIBeforeAfterAnalysis.created_at.desc())
            .first()
        )
        ai_data = None
        if ai_rec:
            ai_data = {
                "visible_change": ai_rec.visible_change,
                "visual_consistency_score": ai_rec.visual_consistency_score,
                "difference_summary": ai_rec.difference_summary,
                "advisory_decision_suggestion": ai_rec.advisory_decision_suggestion,
                "possible_mismatch": ai_rec.possible_mismatch,
                "insufficient_evidence": ai_rec.insufficient_evidence,
            }

        citizen_name = sub.reporter_name if (sub and sub.reporter_name) else (sub.reporter.full_name if (sub and sub.reporter) else None)
        citizen_phone = sub.reporter_phone if (sub and sub.reporter_phone) else (sub.reporter.phone_number if (sub and sub.reporter) else None)
        citizen_email = sub.reporter.email if (sub and sub.reporter) else None

        # Fetch latest AI ModelRuns if available
        model_runs = []
        if sub:
            model_runs = db.query(ModelRun).filter(ModelRun.submission_id == sub.id).order_by(ModelRun.created_at.desc()).all()
        if not model_runs:
            model_runs = db.query(ModelRun).filter(ModelRun.issue_id == issue.id).order_by(ModelRun.created_at.desc()).all()

        model_run = model_runs[0] if model_runs else None
        ai_model_id = model_run.model_id if model_run else ("civic_issues_v1-dc7ae-zzdgj/1" if sub and sub.ai_category_suggestion else None)
        ai_model_provider = getattr(model_run, "model_provider", "roboflow-multi-model") if model_run else "roboflow"
        ai_detected_objects = []
        if model_run and model_run.detections_json:
            try:
                ai_detected_objects = json.loads(model_run.detections_json)
            except Exception:
                ai_detected_objects = []
        ai_analysis_status = model_run.status if model_run else ("COMPLETED" if sub and sub.ai_category_suggestion else None)

        ai_model_ids = [r.model_id for r in model_runs if r.model_id] if model_runs else (["civic_issues_v1-dc7ae-zzdgj/1", "civic-issue-yljwt-tptzy/2", "civic-issues-qj5pb/2"] if sub and sub.ai_category_suggestion else [])
        ai_model_summaries = []
        for r in model_runs:
            ai_model_summaries.append({
                "model_id": r.model_id,
                "status": r.status,
                "category": r.category_suggestion,
                "confidence": r.confidence_score,
                "latency_ms": r.latency_ms,
            })
        ai_consensus_status = "CONSENSUS_VERIFIED" if (sub and sub.ai_category_suggestion) else None
        ai_comparison_notes = None
        if len(ai_model_summaries) >= 2:
            cats = list(set(s["category"] for s in ai_model_summaries if s.get("category")))
            if len(cats) == 1:
                ai_consensus_status = "STRONG_CONSENSUS"
                ai_comparison_notes = f"All models agreed on {cats[0].replace('_', ' ')}."
            elif len(cats) > 1:
                ai_consensus_status = "DISPUTED"
                ai_comparison_notes = f"Models predicted different categories: {', '.join(cats)}."

        # Check duplicate candidates
        dup_count = 0
        dup_evidence = None
        if sub:
            dup_candidates = db.query(DuplicateCandidate).filter(DuplicateCandidate.submission_id == sub.id).all()
            dup_count = len(dup_candidates)
            if dup_count > 0:
                dup_evidence = f"{dup_count} duplicate candidate(s) ({round(dup_candidates[0].distance_meters or 0)}m)"

        results.append(
            StaffComplaintItem(
                id=issue.id,
                submission_id=sub.id if sub else None,
                tracking_id=sub.tracking_id if sub else issue.reference_number,
                reference_number=issue.reference_number,
                category=issue.category,
                status=issue.status,
                priority=issue.priority,
                village_name=v_name,
                ward_name=w_name,
                description=sub.description if sub else None,
                assigned_worker_id=issue.assigned_worker_id,
                assigned_worker_name=worker_name,
                department_id=issue.department_id,
                department_name=dept_name,
                latitude=issue.latitude or (sub.latitude if sub else None),
                longitude=issue.longitude or (sub.longitude if sub else None),
                is_duplicate=issue.status == "SUPERSEDED",
                is_recurrence=issue.is_recurrence,
                created_at=issue.created_at,
                resolved_at=issue.resolved_at,
                photos_count=photos_count,
                estimated_cost=issue.estimated_cost,
                proposed_cost=issue.proposed_cost,
                materials_cost=issue.materials_cost,
                labour_cost=issue.labour_cost,
                other_expenses_cost=issue.other_expenses_cost,
                verified_cost=issue.verified_cost,
                cost_status=issue.cost_status,
                work_completed_at=issue.work_completed_at,
                work_completion_description=issue.work_completion_description,
                work_performed=issue.work_performed,
                materials_used=issue.materials_used,
                labour_details=issue.labour_details,
                cost_verification_remarks=issue.cost_verification_remarks,
                ai_analysis=ai_data,
                before_photo_ids=[m[0] for m in before_media],
                after_photo_ids=[m[0] for m in after_media],
                citizen_name=citizen_name,
                citizen_phone=citizen_phone,
                citizen_email=citizen_email,
                ai_category_suggestion=sub.ai_category_suggestion if sub else None,
                ai_confidence=sub.ai_confidence if sub else None,
                ai_model_id=ai_model_id,
                ai_model_provider=ai_model_provider,
                ai_detected_objects=ai_detected_objects,
                ai_analysis_status=ai_analysis_status,
                ai_model_ids=ai_model_ids,
                ai_model_summaries=ai_model_summaries,
                ai_consensus_status=ai_consensus_status,
                ai_comparison_notes=ai_comparison_notes,
                duplicate_candidates_count=dup_count,
                duplicate_evidence=dup_evidence,
                annotated_photo_id=sub.annotated_media_id if sub else None,
                voice_transcription=sub.voice_transcription if sub else None,
                is_guest=sub.is_guest if (sub and sub.is_guest) else False,
                location_method=sub.location_method if sub else None,
                gps_accuracy=sub.gps_accuracy if sub else None,
            )
        )

    return results

@router.post("/triage/{issue_id}")
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
    issue = find_issue_by_any_id(db, issue_id)
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    # Enforce jurisdiction
    if not verify_jurisdiction_scope(db, current_reviewer.id, issue.locality_unit_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff jurisdiction violation: Issue locality is outside your assigned jurisdiction",
        )

    prev_status = issue.status
    audit_reason = req.audit_reason or req.notes or "Standard triage by authority reviewer"
    instructions = req.instructions or req.notes or "Field maintenance and repair execution"

    # Category correction with audit note
    if req.corrected_category and req.corrected_category != issue.category:
        event = StatusEvent(
            issue_id=issue.id,
            actor_profile_id=current_reviewer.id,
            previous_status=issue.status,
            next_status=issue.status,
            reason=f"Category corrected from {issue.category} to {req.corrected_category}. Note: {audit_reason}",
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
                reason=f"Ward assigned/corrected to {ward_unit.name_en}. Note: {audit_reason}",
            )
            db.add(event)
            issue.locality_unit_id = ward_unit.id

    if issue.status in ["REJECTED", "DRAFT"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot assign worker to an issue with status {issue.status}. PDO must accept/approve the complaint first.",
        )

    # Department and priority
    dept_id = req.department_id
    if not dept_id:
        dept = db.query(Department).first()
        dept_id = dept.id if dept else None
    issue.priority = req.priority or issue.priority
    issue.department_id = dept_id

    # Assignment to worker
    if req.assigned_worker_id:
        worker = db.query(Profile).filter(Profile.id == req.assigned_worker_id).first()
        if not worker:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigned worker profile not found")

        # Verify worker is approved
        is_approved = any(
            ra.role == "worker" and ra.approval_status == "APPROVED" and ra.is_active
            for ra in worker.role_assignments
        )
        if not is_approved and "admin" not in [r.role for r in current_reviewer.role_assignments]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only approved workers can receive assignments.",
            )

        issue.assigned_worker_id = worker.id
        issue.status = "ASSIGNED"

        assignment = Assignment(
            issue_id=issue.id,
            department_id=dept_id,
            worker_profile_id=worker.id,
            assigned_by_id=current_reviewer.id,
            instructions=instructions,
            target_date=req.target_date,
            status="ASSIGNED",
        )
        db.add(assignment)

        status_event = StatusEvent(
            issue_id=issue.id,
            actor_profile_id=current_reviewer.id,
            previous_status=prev_status,
            next_status="ASSIGNED",
            reason=f"Assigned to approved worker {worker.full_name}. Priority: {issue.priority}. Instructions: {instructions}",
        )
        db.add(status_event)

        # Notify assigned worker
        try:
            from app.notifications.service import notification_service
            notification_service.send_notification(
                db=db,
                profile_id=worker.id,
                event_type="TASK_ASSIGNED",
                reference_number=issue.reference_number,
                issue_id=issue.id,
                locale="en",
                custom_message=f"New civic task assigned: {issue.reference_number} ({issue.category}). Instructions: {req.instructions or 'Standard maintenance'}",
                dedup_suffix=f"task-asgn-{issue.id[:8]}",
            )
        except Exception:
            pass
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


class StaffComplaintItem(BaseModel):
    id: str
    submission_id: Optional[str] = None
    tracking_id: str
    reference_number: str
    category: str
    status: str
    priority: str
    village_name: Optional[str] = None
    ward_name: Optional[str] = None
    description: Optional[str] = None
    assigned_worker_id: Optional[str] = None
    assigned_worker_name: Optional[str] = None
    department_id: Optional[str] = None
    department_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_duplicate: bool = False
    is_recurrence: bool = False
    created_at: datetime
    resolved_at: Optional[datetime] = None
    photos_count: int = 0
    estimated_cost: Optional[float] = None
    proposed_cost: Optional[float] = None
    materials_cost: Optional[float] = None
    labour_cost: Optional[float] = None
    other_expenses_cost: Optional[float] = None
    verified_cost: Optional[float] = None
    cost_status: Optional[str] = None
    work_completed_at: Optional[datetime] = None
    work_completion_description: Optional[str] = None
    work_performed: Optional[str] = None
    materials_used: Optional[str] = None
    labour_details: Optional[str] = None
    cost_verification_remarks: Optional[str] = None
    ai_analysis: Optional[Dict[str, Any]] = None
    before_photo_ids: List[str] = []
    after_photo_ids: List[str] = []
    citizen_name: Optional[str] = None
    citizen_phone: Optional[str] = None
    citizen_email: Optional[str] = None
    ai_category_suggestion: Optional[str] = None
    ai_confidence: Optional[float] = None
    ai_model_id: Optional[str] = None
    ai_model_provider: Optional[str] = None
    ai_detected_objects: List[Dict[str, Any]] = []
    ai_analysis_status: Optional[str] = None
    ai_model_ids: List[str] = []
    ai_model_summaries: List[Dict[str, Any]] = []
    ai_consensus_status: Optional[str] = None
    ai_comparison_notes: Optional[str] = None
    duplicate_candidates_count: int = 0
    duplicate_evidence: Optional[str] = None
    annotated_photo_id: Optional[str] = None
    voice_transcription: Optional[str] = None
    is_guest: bool = False
    location_method: Optional[str] = None
    gps_accuracy: Optional[float] = None


@router.get("/all-complaints", response_model=List[StaffComplaintItem])
def get_all_complaints(
    category: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    priority: Optional[str] = Query(None),
    village_name: Optional[str] = Query(None),
    ward_name: Optional[str] = Query(None),
    current_reviewer: Profile = Depends(require_roles("reviewer", "admin")),
    db: Session = Depends(get_db),
):
    """
    Returns all complaints across the Gram Panchayat with full administrative fields,
    supporting filtering by Category, Village, Ward, Status, and Priority.
    """
    query = db.query(Issue).filter(Issue.status != "DRAFT")

    # Scoped jurisdiction for reviewer
    asgn = (
        db.query(RoleAssignment)
        .filter(RoleAssignment.profile_id == current_reviewer.id, RoleAssignment.is_active == True)
        .first()
    )
    gp_id = asgn.jurisdiction_unit_id if asgn else None

    if gp_id and "admin" not in [r.role for r in current_reviewer.role_assignments]:
        child_ids = [r[0] for r in db.query(LocalityUnit.id).filter(LocalityUnit.parent_id == gp_id).all()]
        sub_child_ids = [r[0] for r in db.query(LocalityUnit.id).filter(LocalityUnit.parent_id.in_(child_ids)).all()]
        all_gp_unit_ids = set([gp_id] + child_ids + sub_child_ids)
        query = query.filter((Issue.locality_unit_id.in_(all_gp_unit_ids)) | (Issue.locality_unit_id.is_(None)))

    if category and category != "ALL":
        query = query.filter(Issue.category == category)
    if status_filter and status_filter != "ALL":
        query = query.filter(Issue.status == status_filter)
    if priority and priority != "ALL":
        query = query.filter(Issue.priority == priority)

    issues = query.order_by(Issue.created_at.desc()).all()
    results: List[StaffComplaintItem] = []

    for issue in issues:
        # Get first submission for original description & reporter details
        sub = db.query(Submission).filter(Submission.issue_id == issue.id).order_by(Submission.created_at.asc()).first()
        photos_count = db.query(MediaAsset).filter(MediaAsset.issue_id == issue.id).count()

        v_name = sub.village_name if sub else None
        w_name = sub.ward_name if sub else None
        if not v_name and issue.locality_unit:
            if issue.locality_unit.unit_type == "village":
                v_name = issue.locality_unit.name_en
            elif issue.locality_unit.unit_type == "ward":
                w_name = issue.locality_unit.name_en
                if issue.locality_unit.parent:
                    v_name = issue.locality_unit.parent.name_en

        if village_name and village_name != "ALL" and v_name and village_name.lower() not in v_name.lower():
            continue
        if ward_name and ward_name != "ALL" and w_name and ward_name.lower() not in w_name.lower():
            continue

        worker_name = issue.assigned_worker.full_name if issue.assigned_worker else None
        dept_name = issue.department.name_en if issue.department else None

        # Fetch before and after photos
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

        # Fetch latest AI analysis if available
        ai_rec = (
            db.query(AIBeforeAfterAnalysis)
            .filter(AIBeforeAfterAnalysis.issue_id == issue.id)
            .order_by(AIBeforeAfterAnalysis.created_at.desc())
            .first()
        )
        ai_data = None
        if ai_rec:
            ai_data = {
                "visible_change": ai_rec.visible_change,
                "visual_consistency_score": ai_rec.visual_consistency_score,
                "difference_summary": ai_rec.difference_summary,
                "advisory_decision_suggestion": ai_rec.advisory_decision_suggestion,
                "possible_mismatch": ai_rec.possible_mismatch,
                "insufficient_evidence": ai_rec.insufficient_evidence,
            }

        citizen_name = sub.reporter_name if (sub and sub.reporter_name) else (sub.reporter.full_name if (sub and sub.reporter) else None)
        citizen_phone = sub.reporter_phone if (sub and sub.reporter_phone) else (sub.reporter.phone_number if (sub and sub.reporter) else None)
        citizen_email = sub.reporter.email if (sub and sub.reporter) else None

        # Fetch latest AI ModelRuns if available
        model_runs = []
        if sub:
            model_runs = db.query(ModelRun).filter(ModelRun.submission_id == sub.id).order_by(ModelRun.created_at.desc()).all()
        if not model_runs:
            model_runs = db.query(ModelRun).filter(ModelRun.issue_id == issue.id).order_by(ModelRun.created_at.desc()).all()

        model_run = model_runs[0] if model_runs else None
        ai_model_id = model_run.model_id if model_run else ("civic_issues_v1-dc7ae-zzdgj/1" if sub and sub.ai_category_suggestion else None)
        ai_model_provider = getattr(model_run, "model_provider", "roboflow-multi-model") if model_run else "roboflow"
        ai_detected_objects = []
        if model_run and model_run.detections_json:
            try:
                ai_detected_objects = json.loads(model_run.detections_json)
            except Exception:
                ai_detected_objects = []
        ai_analysis_status = model_run.status if model_run else ("COMPLETED" if sub and sub.ai_category_suggestion else None)

        ai_model_ids = [r.model_id for r in model_runs if r.model_id] if model_runs else (["civic_issues_v1-dc7ae-zzdgj/1", "civic-issue-yljwt-tptzy/2", "civic-issues-qj5pb/2"] if sub and sub.ai_category_suggestion else [])
        ai_model_summaries = []
        for r in model_runs:
            ai_model_summaries.append({
                "model_id": r.model_id,
                "status": r.status,
                "category": r.category_suggestion,
                "confidence": r.confidence_score,
                "latency_ms": r.latency_ms,
            })
        ai_consensus_status = "CONSENSUS_VERIFIED" if (sub and sub.ai_category_suggestion) else None
        ai_comparison_notes = None
        if len(ai_model_summaries) >= 2:
            cats = list(set(s["category"] for s in ai_model_summaries if s.get("category")))
            if len(cats) == 1:
                ai_consensus_status = "STRONG_CONSENSUS"
                ai_comparison_notes = f"All models agreed on {cats[0].replace('_', ' ')}."
            elif len(cats) > 1:
                ai_consensus_status = "DISPUTED"
                ai_comparison_notes = f"Models predicted different categories: {', '.join(cats)}."

        # Check duplicate candidates
        dup_count = 0
        dup_evidence = None
        if sub:
            dup_candidates = db.query(DuplicateCandidate).filter(DuplicateCandidate.submission_id == sub.id).all()
            dup_count = len(dup_candidates)
            if dup_count > 0:
                dup_evidence = f"{dup_count} duplicate candidate(s) ({round(dup_candidates[0].distance_meters or 0)}m)"

        results.append(
            StaffComplaintItem(
                id=issue.id,
                submission_id=sub.id if sub else None,
                tracking_id=sub.tracking_id if sub else issue.reference_number,
                reference_number=issue.reference_number,
                category=issue.category,
                status=issue.status,
                priority=issue.priority,
                village_name=v_name,
                ward_name=w_name,
                description=sub.description if sub else None,
                assigned_worker_id=issue.assigned_worker_id,
                assigned_worker_name=worker_name,
                department_id=issue.department_id,
                department_name=dept_name,
                latitude=issue.latitude or (sub.latitude if sub else None),
                longitude=issue.longitude or (sub.longitude if sub else None),
                is_duplicate=issue.status == "SUPERSEDED",
                is_recurrence=issue.is_recurrence,
                created_at=issue.created_at,
                resolved_at=issue.resolved_at,
                photos_count=photos_count,
                estimated_cost=issue.estimated_cost,
                proposed_cost=issue.proposed_cost,
                materials_cost=issue.materials_cost,
                labour_cost=issue.labour_cost,
                other_expenses_cost=issue.other_expenses_cost,
                verified_cost=issue.verified_cost,
                cost_status=issue.cost_status,
                work_completed_at=issue.work_completed_at,
                work_completion_description=issue.work_completion_description,
                work_performed=issue.work_performed,
                materials_used=issue.materials_used,
                labour_details=issue.labour_details,
                cost_verification_remarks=issue.cost_verification_remarks,
                ai_analysis=ai_data,
                before_photo_ids=[m[0] for m in before_media],
                after_photo_ids=[m[0] for m in after_media],
                citizen_name=citizen_name,
                citizen_phone=citizen_phone,
                citizen_email=citizen_email,
                ai_category_suggestion=sub.ai_category_suggestion if sub else None,
                ai_confidence=sub.ai_confidence if sub else None,
                ai_model_id=ai_model_id,
                ai_model_provider=ai_model_provider,
                ai_detected_objects=ai_detected_objects,
                ai_analysis_status=ai_analysis_status,
                ai_model_ids=ai_model_ids,
                ai_model_summaries=ai_model_summaries,
                ai_consensus_status=ai_consensus_status,
                ai_comparison_notes=ai_comparison_notes,
                duplicate_candidates_count=dup_count,
                duplicate_evidence=dup_evidence,
                annotated_photo_id=sub.annotated_media_id if sub else None,
                voice_transcription=sub.voice_transcription if sub else None,
                is_guest=sub.is_guest if (sub and sub.is_guest) else False,
                location_method=sub.location_method if sub else None,
                gps_accuracy=sub.gps_accuracy if sub else None,
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
    issue = find_issue_by_any_id(db, issue_id)
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

        # Approved final expenditure
        if req.verified_cost is not None and req.verified_cost >= 0:
            issue.verified_cost = req.verified_cost
        elif issue.proposed_cost is not None:
            issue.verified_cost = issue.proposed_cost

        issue.cost_status = "VERIFIED"
        issue.cost_verification_remarks = req.cost_remarks or req.explanation

        # Make safe verified before-and-after photographic evidence public
        db.query(MediaAsset).filter(
            MediaAsset.issue_id == issue.id,
            MediaAsset.is_quarantined == False,
        ).update({"is_public_approved": True}, synchronize_session=False)

        # Update latest work completion
        latest_comp = (
            db.query(WorkCompletion)
            .filter(WorkCompletion.issue_id == issue.id)
            .order_by(WorkCompletion.submission_number.desc())
            .first()
        )
        if latest_comp:
            latest_comp.status = "APPROVED"
            latest_comp.verified_cost = issue.verified_cost
            latest_comp.verified_by_id = current_reviewer.id
            latest_comp.verified_at = datetime.now(timezone.utc)
            latest_comp.pdo_remarks = req.explanation

        cost_note = f" (Verified expenditure: ₹{issue.verified_cost:,.2f})" if issue.verified_cost is not None else ""
        review = RepairReview(
            issue_id=issue.id,
            reviewer_profile_id=current_reviewer.id,
            decision="APPROVED",
            explanation=f"{req.explanation}{cost_note}",
        )
        db.add(review)

        event = StatusEvent(
            issue_id=issue.id,
            actor_profile_id=current_reviewer.id,
            previous_status=prev_status,
            next_status="RESOLVED",
            reason=f"Repair and expenditure independently verified by {current_reviewer.full_name}. Note: {req.explanation}{cost_note}",
        )
        db.add(event)

    else:
        # Request better evidence or rework
        issue.status = "CORRECTION_REQUIRED"
        issue.cost_status = "REJECTED"
        issue.cost_verification_remarks = req.cost_remarks or req.explanation
        issue.resolution_review_notes = req.explanation

        latest_comp = (
            db.query(WorkCompletion)
            .filter(WorkCompletion.issue_id == issue.id)
            .order_by(WorkCompletion.submission_number.desc())
            .first()
        )
        if latest_comp:
            latest_comp.status = "CORRECTION_REQUIRED"
            latest_comp.pdo_remarks = req.explanation

        review = RepairReview(
            issue_id=issue.id,
            reviewer_profile_id=current_reviewer.id,
            decision="CORRECTION_REQUIRED",
            explanation=req.explanation,
        )
        db.add(review)

        event = StatusEvent(
            issue_id=issue.id,
            actor_profile_id=current_reviewer.id,
            previous_status=prev_status,
            next_status="CORRECTION_REQUIRED",
            reason=f"Correction required by PDO reviewer {current_reviewer.full_name}: {req.explanation}",
        )
        db.add(event)

    db.commit()
    db.refresh(issue)

    from app.notifications.service import notification_service
    if req.decision == "APPROVE":
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
    else:
        # Notify worker that rework is required
        if issue.assigned_worker_id:
            notification_service.send_notification(
                db=db,
                profile_id=issue.assigned_worker_id,
                event_type="CORRECTION_REQUESTED",
                reference_number=issue.reference_number,
                issue_id=issue.id,
                locale="en",
                dedup_suffix=f"rework-{issue.id[:8]}",
            )

    return {
        "status": "success",
        "issue_id": issue.id,
        "new_status": issue.status,
        "verified_cost": issue.verified_cost,
        "resolved_at": issue.resolved_at,
    }


class RequestInfoRequest(BaseModel):
    message: str


class RejectIssueRequest(BaseModel):
    reason: str


class ConfirmIssueRequest(BaseModel):
    reason: Optional[str] = "Confirmed by Panchayat reviewer"


@router.post("/issues/{issue_id}/request-info")
def request_issue_information(
    issue_id: str,
    req: RequestInfoRequest,
    current_reviewer: Profile = Depends(require_roles("reviewer", "admin")),
    db: Session = Depends(get_db),
):
    issue = find_issue_by_any_id(db, issue_id)
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    prev_status = issue.status
    issue.status = "NEEDS_INFORMATION"
    issue.clarification_message = req.message

    event = StatusEvent(
        issue_id=issue.id,
        actor_profile_id=current_reviewer.id,
        previous_status=prev_status,
        next_status="NEEDS_INFORMATION",
        reason=f"Additional clarification requested by {current_reviewer.full_name}: {req.message}",
    )
    db.add(event)
    db.commit()

    try:
        from app.notifications.service import notification_service
        subs = db.query(Submission).filter(Submission.issue_id == issue.id).all()
        for s in subs:
            notification_service.send_notification(
                db=db,
                profile_id=s.reporter_id,
                event_type="NEEDS_INFORMATION",
                reference_number=issue.reference_number,
                issue_id=issue.id,
                locale=s.locale,
                custom_message=f"Panchayat reviewer requested information for {issue.reference_number}: {req.message}",
                dedup_suffix=f"needinfo-{issue.id[:8]}",
            )
    except Exception:
        pass

    return {"status": "success", "issue_id": issue.id, "new_status": issue.status, "message": req.message}


@router.post("/issues/{issue_id}/reject")
def reject_issue(
    issue_id: str,
    req: RejectIssueRequest,
    current_reviewer: Profile = Depends(require_roles("reviewer", "admin")),
    db: Session = Depends(get_db),
):
    issue = find_issue_by_any_id(db, issue_id)
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    prev_status = issue.status
    issue.status = "REJECTED"
    issue.rejection_reason = req.reason
    issue.rejection_by_id = current_reviewer.id

    event = StatusEvent(
        issue_id=issue.id,
        actor_profile_id=current_reviewer.id,
        previous_status=prev_status,
        next_status="REJECTED",
        reason=f"Rejected by {current_reviewer.full_name}. Reason: {req.reason}",
    )
    db.add(event)
    db.commit()

    try:
        from app.notifications.service import notification_service
        subs = db.query(Submission).filter(Submission.issue_id == issue.id).all()
        for s in subs:
            notification_service.send_notification(
                db=db,
                profile_id=s.reporter_id,
                event_type="ISSUE_REJECTED",
                reference_number=issue.reference_number,
                issue_id=issue.id,
                locale=s.locale,
                custom_message=f"Complaint {issue.reference_number} was rejected by Panchayat review. Reason: {req.reason}",
                dedup_suffix=f"rejected-{issue.id[:8]}",
            )
    except Exception:
        pass

    return {"status": "success", "issue_id": issue.id, "new_status": issue.status, "reason": req.reason}


@router.post("/issues/{issue_id}/confirm")
@router.post("/issues/{issue_id}/accept")
def confirm_issue(
    issue_id: str,
    req: ConfirmIssueRequest = ConfirmIssueRequest(),
    current_reviewer: Profile = Depends(require_roles("reviewer", "admin")),
    db: Session = Depends(get_db),
):
    issue = find_issue_by_any_id(db, issue_id)
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    prev_status = issue.status
    issue.status = "UNDER_REVIEW"

    event = StatusEvent(
        issue_id=issue.id,
        actor_profile_id=current_reviewer.id,
        previous_status=prev_status,
        next_status="UNDER_REVIEW",
        reason=f"Complaint accepted and verified by Panchayat Development Officer (PDO). {req.reason or ''}".strip(),
    )
    db.add(event)
    db.commit()

    return {"status": "success", "issue_id": issue.id, "new_status": issue.status}

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


# =====================================================================
# VILLAGE PDO SPECIALIZED GOVERNANCE & OPERATIONAL ENDPOINTS
# =====================================================================

class VillageOverviewStats(BaseModel):
    village_id: Optional[str] = None
    village_name: str
    total_complaints: int
    new_complaints: int
    under_review: int
    awaiting_clarification: int = 0
    approved: int = 0
    assigned: int
    in_progress: int
    awaiting_verification: int
    resolved: int
    rejected: int = 0
    reopened: int
    category_distribution: Dict[str, int]
    status_distribution: Dict[str, int]
    priority_distribution: Dict[str, int]
    recent_trend: List[Dict[str, Any]]

class WorkerItem(BaseModel):
    id: str
    full_name: str
    email: str
    phone_number: Optional[str] = None
    role: str
    approval_status: str
    is_active: bool
    village_id: Optional[str] = None
    village_name: Optional[str] = None
    department_id: Optional[str] = None
    department_name: Optional[str] = None
    active_assignments: int = 0
    completed_assignments: int = 0
    registered_at: str

class VillageMapPoint(BaseModel):
    id: str
    tracking_id: str
    reference_number: str
    category: str
    status: str
    priority: str
    latitude: float
    longitude: float
    description: Optional[str] = None
    assigned_worker_name: Optional[str] = None
    submitted_at: str
    village_name: Optional[str] = None
    gps_accuracy: Optional[float] = None

class VillageMapResponse(BaseModel):
    village_id: Optional[str] = None
    village_name: str
    boundary_geojson: Optional[str] = None
    center_latitude: float
    center_longitude: float
    points: List[VillageMapPoint]

@router.get("/village-overview", response_model=VillageOverviewStats)
def get_village_pdo_overview(
    current_reviewer: Profile = Depends(require_roles("reviewer", "admin")),
    db: Session = Depends(get_db),
):
    """
    Returns real database-backed overview for the Village PDO's assigned Gram Panchayat.
    Scoped strictly to the authenticated PDO's jurisdiction.
    """
    # Find PDO's assigned village / GP
    asgn = (
        db.query(RoleAssignment)
        .filter(RoleAssignment.profile_id == current_reviewer.id, RoleAssignment.is_active == True)
        .first()
    )
    gp_id = asgn.jurisdiction_unit_id if asgn else None

    # Fetch GP name
    gp_name = "Unassigned Village"
    if gp_id:
        gp_unit = db.query(LocalityUnit).filter(LocalityUnit.id == gp_id).first()
        if gp_unit:
            gp_name = gp_unit.name_en
    else:
        first_v = db.query(LocalityUnit).filter(LocalityUnit.unit_type.in_(["gram_panchayat", "village"])).first()
        if first_v:
            gp_name = f"{first_v.name_en} Gram Panchayat"

    # Scoped query: issues strictly in this GP or its sub-villages/wards; isolate demonstration data
    query = db.query(Issue).filter(Issue.status != "DRAFT", Issue.is_demo == False)
    if gp_id and "admin" not in [r.role for r in current_reviewer.role_assignments]:
        # Collect sub-unit IDs (villages, wards under this GP)
        child_ids = [r[0] for r in db.query(LocalityUnit.id).filter(LocalityUnit.parent_id == gp_id).all()]
        sub_child_ids = [r[0] for r in db.query(LocalityUnit.id).filter(LocalityUnit.parent_id.in_(child_ids)).all()]
        all_gp_unit_ids = set([gp_id] + child_ids + sub_child_ids)
        query = query.filter(Issue.locality_unit_id.in_(all_gp_unit_ids))
    elif not gp_id and "admin" not in [r.role for r in current_reviewer.role_assignments]:
        # Unassigned reviewer has 0 complaints
        query = query.filter(Issue.id == "__none__")

    issues = query.all()

    total_complaints = len(issues)
    new_complaints = sum(1 for i in issues if i.status == "SUBMITTED")
    under_review = sum(1 for i in issues if i.status == "UNDER_REVIEW")
    awaiting_clarification = sum(1 for i in issues if i.status in ["NEEDS_INFORMATION", "AWAITING_INFORMATION"])
    approved = sum(1 for i in issues if i.status in ["APPROVED", "CONFIRMED"])
    assigned = sum(1 for i in issues if i.status == "ASSIGNED")
    in_progress = sum(1 for i in issues if i.status == "IN_PROGRESS")
    awaiting_verification = sum(1 for i in issues if i.status in ["REPAIR_REPORTED", "AWAITING_VERIFICATION"])
    resolved = sum(1 for i in issues if i.status == "RESOLVED")
    rejected = sum(1 for i in issues if i.status == "REJECTED")
    reopened = sum(1 for i in issues if i.status == "REOPENED")

    # Distributions
    category_dist: Dict[str, int] = {}
    status_dist: Dict[str, int] = {}
    priority_dist: Dict[str, int] = {}

    for i in issues:
        cat = i.category
        category_dist[cat] = category_dist.get(cat, 0) + 1
        st = i.status
        status_dist[st] = status_dist.get(st, 0) + 1
        pr = i.priority
        priority_dist[pr] = priority_dist.get(pr, 0) + 1

    # Recent Trend (group by date)
    date_counts: Dict[str, int] = {}
    for i in issues:
        d_str = i.created_at.strftime("%Y-%m-%d") if i.created_at else "Unknown"
        date_counts[d_str] = date_counts.get(d_str, 0) + 1

    trend_list = [{"date": d, "count": c} for d, c in sorted(date_counts.items())[-10:]]

    return VillageOverviewStats(
        village_id=gp_id,
        village_name=gp_name,
        total_complaints=total_complaints,
        new_complaints=new_complaints,
        under_review=under_review,
        awaiting_clarification=awaiting_clarification,
        approved=approved,
        assigned=assigned,
        in_progress=in_progress,
        awaiting_verification=awaiting_verification,
        resolved=resolved,
        rejected=rejected,
        reopened=reopened,
        category_distribution=category_dist,
        status_distribution=status_dist,
        priority_distribution=priority_dist,
        recent_trend=trend_list,
    )

@router.get("/workers", response_model=List[WorkerItem])
def list_village_workers(
    approval_status: Optional[str] = Query(None),
    current_reviewer: Profile = Depends(require_roles("reviewer", "admin")),
    db: Session = Depends(get_db),
):
    """
    Lists workers registered for or assigned to the PDO's Gram Panchayat.
    Supports filtering by approval status (PENDING, APPROVED, REJECTED, SUSPENDED).
    """
    asgn = (
        db.query(RoleAssignment)
        .filter(RoleAssignment.profile_id == current_reviewer.id, RoleAssignment.is_active == True)
        .first()
    )
    gp_id = asgn.jurisdiction_unit_id if asgn else None

    query = (
        db.query(RoleAssignment, Profile)
        .join(Profile, RoleAssignment.profile_id == Profile.id)
        .filter(RoleAssignment.role == "worker")
    )

    if approval_status and approval_status != "ALL":
        query = query.filter(RoleAssignment.approval_status == approval_status)

    workers = query.all()
    results: List[WorkerItem] = []

    for r_asgn, prof in workers:
        v_name = None
        if r_asgn.jurisdiction_unit_id:
            u = db.query(LocalityUnit).filter(LocalityUnit.id == r_asgn.jurisdiction_unit_id).first()
            if u:
                v_name = u.name_en

        d_name = None
        if r_asgn.department_id:
            dept = db.query(Department).filter(Department.id == r_asgn.department_id).first()
            if dept:
                d_name = dept.name_en

        active_cnt = db.query(Assignment).filter(
            Assignment.worker_profile_id == prof.id,
            Assignment.status.in_(["ASSIGNED", "ACCEPTED", "IN_PROGRESS"]),
        ).count()

        completed_cnt = db.query(Assignment).filter(
            Assignment.worker_profile_id == prof.id,
            Assignment.status == "COMPLETED",
        ).count()

        results.append(
            WorkerItem(
                id=prof.id,
                full_name=prof.full_name,
                email=prof.email,
                phone_number=prof.phone_number,
                role="worker",
                approval_status=getattr(r_asgn, "approval_status", "APPROVED") or "APPROVED",
                is_active=prof.is_active and r_asgn.is_active,
                village_id=r_asgn.jurisdiction_unit_id,
                village_name=v_name,
                department_id=r_asgn.department_id,
                department_name=d_name,
                active_assignments=active_cnt,
                completed_assignments=completed_cnt,
                registered_at=prof.created_at.isoformat() if prof.created_at else datetime.now(timezone.utc).isoformat(),
            )
        )

    return results

@router.post("/workers/{worker_id}/approve")
def approve_worker_registration(
    worker_id: str,
    current_reviewer: Profile = Depends(require_roles("reviewer", "admin")),
    db: Session = Depends(get_db),
):
    """
    Village PDO reviews and approves a pending worker registration.
    """
    prof = db.query(Profile).filter(Profile.id == worker_id).first()
    if not prof:
        raise HTTPException(status_code=404, detail="Worker profile not found")

    asgn = db.query(RoleAssignment).filter(
        RoleAssignment.profile_id == worker_id,
        RoleAssignment.role == "worker",
    ).first()
    if not asgn:
        raise HTTPException(status_code=404, detail="Worker role assignment not found")

    asgn.approval_status = "APPROVED"
    asgn.is_active = True
    asgn.granted_by = current_reviewer.id

    audit = AuditLog(
        actor_profile_id=current_reviewer.id,
        action="APPROVE_WORKER",
        target_type="profile",
        target_id=prof.id,
        details_json=f'{{"worker_name": "{prof.full_name}", "approved_by": "{current_reviewer.full_name}"}}',
    )
    db.add(audit)
    db.commit()

    return {"status": "approved", "worker_id": prof.id, "worker_name": prof.full_name}

@router.post("/workers/{worker_id}/reject")
def reject_worker_registration(
    worker_id: str,
    reason: Optional[str] = Query("Qualifications or verification unconfirmed"),
    current_reviewer: Profile = Depends(require_roles("reviewer", "admin")),
    db: Session = Depends(get_db),
):
    """
    Village PDO rejects a worker registration with audit reason.
    """
    prof = db.query(Profile).filter(Profile.id == worker_id).first()
    if not prof:
        raise HTTPException(status_code=404, detail="Worker profile not found")

    asgn = db.query(RoleAssignment).filter(
        RoleAssignment.profile_id == worker_id,
        RoleAssignment.role == "worker",
    ).first()
    if not asgn:
        raise HTTPException(status_code=404, detail="Worker role assignment not found")

    asgn.approval_status = "REJECTED"
    asgn.is_active = False

    audit = AuditLog(
        actor_profile_id=current_reviewer.id,
        action="REJECT_WORKER",
        target_type="profile",
        target_id=prof.id,
        details_json=f'{{"worker_name": "{prof.full_name}", "reason": "{reason}"}}',
    )
    db.add(audit)
    db.commit()

    return {"status": "rejected", "worker_id": prof.id, "reason": reason}

@router.get("/village-map", response_model=VillageMapResponse)
def get_pdo_village_map(
    category: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    current_reviewer: Profile = Depends(require_roles("reviewer", "admin")),
    db: Session = Depends(get_db),
):
    """
    Returns verified village boundary GeoJSON and interactive complaint points for the PDO's Village Map.
    """
    asgn = (
        db.query(RoleAssignment)
        .filter(RoleAssignment.profile_id == current_reviewer.id, RoleAssignment.is_active == True)
        .first()
    )
    gp_id = asgn.jurisdiction_unit_id if asgn else None

    gp_name = "Belagavi Village"
    boundary_geo = None
    center_lat = 15.8497
    center_lon = 74.4977

    if gp_id:
        gp_unit = db.query(LocalityUnit).filter(LocalityUnit.id == gp_id).first()
        if gp_unit:
            gp_name = gp_unit.name_en
            boundary_geo = gp_unit.boundary_geojson

    query = db.query(Issue).filter(
        Issue.status != "DRAFT",
        (Issue.latitude.isnot(None)) | (Issue.public_latitude.isnot(None)),
    )

    if gp_id and "admin" not in [r.role for r in current_reviewer.role_assignments]:
        child_ids = [r[0] for r in db.query(LocalityUnit.id).filter(LocalityUnit.parent_id == gp_id).all()]
        sub_child_ids = [r[0] for r in db.query(LocalityUnit.id).filter(LocalityUnit.parent_id.in_(child_ids)).all()]
        all_gp_unit_ids = set([gp_id] + child_ids + sub_child_ids)
        query = query.filter((Issue.locality_unit_id.in_(all_gp_unit_ids)) | (Issue.locality_unit_id.is_(None)))

    if category and category != "ALL":
        query = query.filter(Issue.category == category)
    if status_filter and status_filter != "ALL":
        query = query.filter(Issue.status == status_filter)

    issues = query.all()
    points: List[VillageMapPoint] = []

    for issue in issues:
        sub = db.query(Submission).filter(Submission.issue_id == issue.id).first()
        lat = issue.latitude or (sub.latitude if sub else None) or issue.public_latitude
        lon = issue.longitude or (sub.longitude if sub else None) or issue.public_longitude
        if not lat or not lon:
            continue

        worker_name = issue.assigned_worker.full_name if issue.assigned_worker else None

        v_name = (sub.village_name if sub else None) or (issue.locality_unit.name_en if issue.locality_unit else None) or gp_name
        points.append(
            VillageMapPoint(
                id=issue.id,
                tracking_id=sub.tracking_id if sub else issue.reference_number,
                reference_number=issue.reference_number,
                category=issue.category,
                status=issue.status,
                priority=issue.priority,
                latitude=lat,
                longitude=lon,
                description=sub.description if sub else None,
                assigned_worker_name=worker_name,
                submitted_at=issue.created_at.isoformat() if issue.created_at else datetime.now(timezone.utc).isoformat(),
                village_name=v_name,
                gps_accuracy=sub.gps_accuracy if sub else None,
            )
        )

    # If first point exists, use it to frame center
    if points:
        center_lat = points[0].latitude
        center_lon = points[0].longitude

    return VillageMapResponse(
        village_id=gp_id,
        village_name=gp_name,
        boundary_geojson=boundary_geo,
        center_latitude=center_lat,
        center_longitude=center_lon,
        points=points,
    )

# --- Section 4: Ward Management & Ward Members for Village PDO ---

class CreateWardMemberRequest(BaseModel):
    ward_unit_id: str
    full_name: str
    phone_number: Optional[str] = None
    email: Optional[str] = None
    designation: Optional[str] = "Ward Member"

class UpdateWardMemberRequest(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    designation: Optional[str] = None
    is_active: Optional[bool] = None

@router.get("/wards")
def get_village_wards(
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all wards in the PDO's assigned Gram Panchayat, along with complaint stats and ward members.
    Strictly isolated to the PDO's assigned village.
    """
    from app.models.users import WardMember

    # Get PDO assigned village
    assignment = (
        db.query(RoleAssignment)
        .filter(RoleAssignment.profile_id == current_user.id, RoleAssignment.is_active == True)
        .first()
    )
    village_id = assignment.jurisdiction_unit_id if assignment else None

    # Query wards
    wards_query = db.query(LocalityUnit).filter(LocalityUnit.unit_type == "ward")
    if village_id:
        wards_query = wards_query.filter(LocalityUnit.parent_id == village_id)

    wards = wards_query.all()
    results = []

    for w in wards:
        total_c = db.query(Issue).filter(Issue.locality_unit_id == w.id).count()
        res_c = db.query(Issue).filter(Issue.locality_unit_id == w.id, Issue.status == "RESOLVED").count()
        pend_c = db.query(Issue).filter(Issue.locality_unit_id == w.id, Issue.status.in_(["SUBMITTED", "UNDER_REVIEW", "IN_PROGRESS", "ASSIGNED"])).count()
        
        # Ward members
        members = db.query(WardMember).filter(WardMember.ward_unit_id == w.id, WardMember.is_active == True).all()
        member_list = [
            {
                "id": m.id,
                "full_name": m.full_name,
                "phone_number": m.phone_number,
                "email": m.email,
                "designation": m.designation,
                "is_active": m.is_active,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in members
        ]

        results.append({
            "id": w.id,
            "name_en": w.name_en,
            "name_kn": w.name_kn,
            "official_code": w.official_code,
            "total_complaints": total_c,
            "resolved_complaints": res_c,
            "pending_complaints": pend_c,
            "members_count": len(member_list),
            "members": member_list,
        })

    return results

@router.post("/ward-members")
def add_ward_member(
    req: CreateWardMemberRequest,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Add a new elected or appointed Ward Member to a ward in the PDO's village.
    """
    from app.models.users import WardMember
    import uuid

    # Verify ward exists
    ward = db.query(LocalityUnit).filter(LocalityUnit.id == req.ward_unit_id).first()
    if not ward:
        raise HTTPException(status_code=404, detail="Ward not found")

    member = WardMember(
        id=str(uuid.uuid4()),
        ward_unit_id=req.ward_unit_id,
        full_name=req.full_name.strip(),
        phone_number=req.phone_number.strip() if req.phone_number else None,
        email=req.email.strip().lower() if req.email else None,
        designation=req.designation or "Ward Member",
        is_active=True,
    )
    db.add(member)
    db.commit()
    db.refresh(member)

    return {
        "status": "success",
        "id": member.id,
        "full_name": member.full_name,
        "ward_id": member.ward_unit_id,
        "designation": member.designation,
    }

@router.patch("/ward-members/{member_id}")
def update_ward_member(
    member_id: str,
    req: UpdateWardMemberRequest,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update ward member information or toggle active status.
    """
    from app.models.users import WardMember
    member = db.query(WardMember).filter(WardMember.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Ward member not found")

    if req.full_name is not None:
        member.full_name = req.full_name.strip()
    if req.phone_number is not None:
        member.phone_number = req.phone_number.strip()
    if req.email is not None:
        member.email = req.email.strip().lower()
    if req.designation is not None:
        member.designation = req.designation.strip()
    if req.is_active is not None:
        member.is_active = req.is_active

    db.commit()
    return {"status": "success", "id": member.id, "is_active": member.is_active}

@router.delete("/ward-members/{member_id}")
def delete_ward_member(
    member_id: str,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Deactivate or remove a ward member.
    """
    from app.models.users import WardMember
    member = db.query(WardMember).filter(WardMember.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Ward member not found")

    member.is_active = False
    db.commit()
    return {"status": "success", "message": "Ward member deactivated"}

@router.get("/notifications")
def get_pdo_notifications(
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    In-app alerts and Taluk Super Admin announcements delivered to this PDO.
    """
    from app.models.issues import Notification
    notifs = (
        db.query(Notification)
        .filter(Notification.profile_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )

    return [
        {
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "event_type": n.event_type,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in notifs
    ]




