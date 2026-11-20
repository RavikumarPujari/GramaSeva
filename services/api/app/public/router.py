import os
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.models.issues import Issue, Submission, MediaAsset, StatusEvent, AIBeforeAfterAnalysis
from app.models.localities import LocalityUnit, Department
from app.core.sla import compute_sla_status
from app.storage.service import storage_service

router = APIRouter(prefix="/public", tags=["Sanitized Public Transparency"])

# Public Projection Schemas (Zero Private Data)
class PublicMediaItem(BaseModel):
    id: str
    evidence_role: str
    mime_type: str
    view_url: str

class PublicTimelineItem(BaseModel):
    status: str
    timestamp: datetime
    actor_title: str
    public_summary: Optional[str] = None

class PublicIssueSummary(BaseModel):
    id: str
    reference_number: str
    category: str
    status: str
    priority: str
    description: Optional[str] = None
    village_name: Optional[str] = None
    ward_name: Optional[str] = None
    public_latitude: Optional[float] = None
    public_longitude: Optional[float] = None
    submissions_count: int
    approved_media_count: int
    thumbnail_url: Optional[str] = None
    after_thumbnail_url: Optional[str] = None
    has_after_photo: bool = False
    reporter_display_name: str = "Verified Citizen"
    assigned_worker_display_name: Optional[str] = None
    estimated_cost: Optional[float] = None
    proposed_cost: Optional[float] = None
    verified_cost: Optional[float] = None
    cost_status: str = "UNRECORDED"
    work_completed_at: Optional[datetime] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None
    sla_status: Dict[str, Any]

class PublicIssueDetail(BaseModel):
    id: str
    reference_number: str
    category: str
    status: str
    priority: str
    village_name: Optional[str] = None
    ward_name: Optional[str] = None
    public_latitude: Optional[float] = None
    public_longitude: Optional[float] = None
    submissions_count: int
    created_at: datetime
    resolved_at: Optional[datetime] = None
    sla_status: Dict[str, Any]
    timeline: List[PublicTimelineItem]
    approved_media: List[PublicMediaItem]
    before_photos: List[PublicMediaItem] = []
    after_photos: List[PublicMediaItem] = []
    thumbnail_url: Optional[str] = None
    after_thumbnail_url: Optional[str] = None
    has_after_photo: bool = False
    reporter_display_name: str = "Verified Citizen"
    assigned_worker_display_name: Optional[str] = None
    estimated_cost: Optional[float] = None
    proposed_cost: Optional[float] = None
    verified_cost: Optional[float] = None
    cost_status: str = "UNRECORDED"
    work_completed_at: Optional[datetime] = None
    work_completion_description: Optional[str] = None
    work_performed: Optional[str] = None
    materials_used: Optional[str] = None
    labour_details: Optional[str] = None
    materials_cost: Optional[float] = None
    labour_cost: Optional[float] = None
    other_expenses_cost: Optional[float] = None
    cost_verification_remarks: Optional[str] = None
    ai_observation_summary: Optional[str] = None
    ai_visual_consistency_score: Optional[float] = None
    pdo_officer_title: str = "Village Panchayat Development Officer (PDO)"
    verification_date: Optional[datetime] = None

class VillageMetric(BaseModel):
    village_name: str
    issues_count: int
    resolved_count: int
    overdue_count: int

class WardMetric(BaseModel):
    ward_name: str
    village_name: Optional[str] = None
    issues_count: int
    resolved_count: int

class CategoryMetric(BaseModel):
    category: str
    count: int
    resolved_count: int

class DepartmentMetric(BaseModel):
    department_name: str
    assigned_count: int
    resolved_count: int

class PublicAnalyticsResponse(BaseModel):
    total_unique_issues: int
    total_submissions: int
    open_issues: int
    repair_reported_issues: int
    resolved_issues: int
    reopened_issues: int
    overdue_issues: int
    average_resolution_hours: float
    by_village: List[VillageMetric]
    by_ward: List[WardMetric]
    by_category: List[CategoryMetric]
    by_department: List[DepartmentMetric]

class LocalityUnitItem(BaseModel):
    id: str
    unit_type: str
    name_en: str
    name_kn: Optional[str] = None
    name_hi: Optional[str] = None
    parent_id: Optional[str] = None

@router.get("/issues", response_model=List[PublicIssueSummary])
def get_public_issues(
    village_name: Optional[str] = Query(None),
    ward_name: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    date_range: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Returns sanitized public projection of issues for the Public Civic Works Tracker.
    Excludes DRAFTs. Generalizes coordinates (~100m) and strictly protects citizen privacy.
    Only displays verified expenditure when officially approved by PDO.
    """
    v_filter = village_name if isinstance(village_name, str) and village_name != "ALL" else None
    w_filter = ward_name if isinstance(ward_name, str) and ward_name != "ALL" else None
    cat_filter = category if isinstance(category, str) and category != "ALL" else None
    stat_filter = status_filter if isinstance(status_filter, str) and status_filter != "ALL" else None
    search_q = search.strip().lower() if isinstance(search, str) and search.strip() else None
    lim = limit if isinstance(limit, int) else 100
    off = offset if isinstance(offset, int) else 0

    query = db.query(Issue).filter(Issue.status != "DRAFT")

    if cat_filter:
        query = query.filter(Issue.category == cat_filter)
    if stat_filter:
        if stat_filter == "AWAITING_VERIFICATION":
            query = query.filter(Issue.status.in_(["REPAIR_REPORTED", "AWAITING_VERIFICATION"]))
        elif stat_filter == "NEW":
            query = query.filter(Issue.status == "SUBMITTED")
        else:
            query = query.filter(Issue.status == stat_filter)

    # Date Range filtering
    if date_range and date_range != "all":
        now = datetime.now(timezone.utc)
        if date_range == "7d":
            query = query.filter(Issue.created_at >= now - timedelta(days=7))
        elif date_range == "30d":
            query = query.filter(Issue.created_at >= now - timedelta(days=30))
        elif date_range == "90d":
            query = query.filter(Issue.created_at >= now - timedelta(days=90))
        elif date_range == "1y":
            query = query.filter(Issue.created_at >= now - timedelta(days=365))

    issues = query.order_by(Issue.created_at.desc()).offset(off).limit(lim).all()

    result: List[PublicIssueSummary] = []
    for issue in issues:
        # Resolve locality names
        loc = issue.locality_unit
        v_name = None
        w_name = None
        if loc:
            if loc.unit_type in ("village", "gram_panchayat"):
                v_name = loc.name_en
            elif loc.unit_type == "ward":
                w_name = loc.name_en
                if loc.parent:
                    v_name = loc.parent.name_en

        # Apply in-memory locality filters
        if v_filter and v_name and v_filter.lower() not in v_name.lower():
            continue
        if w_filter and w_name and w_filter.lower() not in w_name.lower():
            continue

        # Get first submission for description and citizen consent
        sub = db.query(Submission).filter(Submission.issue_id == issue.id).order_by(Submission.created_at.asc()).first()
        sub_desc = sub.description if sub else None

        # Apply search query across reference_number, category, village, and description
        if search_q:
            ref_match = search_q in issue.reference_number.lower()
            cat_match = search_q in issue.category.lower()
            vill_match = bool(v_name and search_q in v_name.lower())
            desc_match = bool(sub_desc and search_q in sub_desc.lower())
            if not (ref_match or cat_match or vill_match or desc_match):
                continue

        # Coordinate generalization (~100m precision to prevent home pinpointing)
        gen_lat = round(issue.public_latitude or issue.latitude, 3) if (issue.public_latitude or issue.latitude) else None
        gen_lng = round(issue.public_longitude or issue.longitude, 3) if (issue.public_longitude or issue.longitude) else None

        submissions_count = db.query(Submission).filter(Submission.issue_id == issue.id).count()
        approved_media_count = (
            db.query(MediaAsset)
            .filter(
                MediaAsset.issue_id == issue.id,
                MediaAsset.is_quarantined == False,
            )
            .count()
        )

        # Before image thumbnail
        before_photo = (
            db.query(MediaAsset)
            .filter(
                MediaAsset.issue_id == issue.id,
                MediaAsset.evidence_role == "CITIZEN_BEFORE",
                MediaAsset.is_quarantined == False,
            )
            .order_by(MediaAsset.created_at.asc())
            .first()
        )
        thumbnail_url = f"/api/v1/public/media/{before_photo.id}/view" if before_photo else None

        # After image thumbnail
        after_photo = (
            db.query(MediaAsset)
            .filter(
                MediaAsset.issue_id == issue.id,
                MediaAsset.evidence_role == "WORKER_AFTER",
                MediaAsset.is_quarantined == False,
            )
            .order_by(MediaAsset.created_at.desc())
            .first()
        )
        after_thumbnail_url = f"/api/v1/public/media/{after_photo.id}/view" if after_photo else None
        has_after_photo = after_photo is not None

        # Citizen privacy protection: only disclose real name if consent is given
        has_consent = bool(issue.public_display_consent or (sub and sub.public_display_consent))
        if has_consent and sub and sub.reporter and sub.reporter.full_name:
            reporter_name = sub.reporter.full_name
        else:
            reporter_name = "Verified Citizen"

        # Assigned worker disclosure
        worker_name = "Assigned Field Staff" if issue.assigned_worker_id else None

        sla = compute_sla_status(
            created_at=issue.created_at,
            category=issue.category,
            priority=issue.priority,
            current_status=issue.status,
            resolved_at=issue.resolved_at,
        )

        result.append(
            PublicIssueSummary(
                id=issue.id,
                reference_number=issue.reference_number,
                category=issue.category,
                status=issue.status,
                priority=issue.priority,
                description=sub_desc,
                village_name=v_name,
                ward_name=w_name,
                public_latitude=gen_lat,
                public_longitude=gen_lng,
                submissions_count=max(submissions_count, 1),
                approved_media_count=approved_media_count,
                thumbnail_url=thumbnail_url,
                after_thumbnail_url=after_thumbnail_url,
                has_after_photo=has_after_photo,
                reporter_display_name=reporter_name,
                assigned_worker_display_name=worker_name,
                estimated_cost=issue.estimated_cost,
                proposed_cost=issue.proposed_cost,
                verified_cost=issue.verified_cost if issue.cost_status == "VERIFIED" else None,
                cost_status=issue.cost_status or "UNRECORDED",
                work_completed_at=issue.work_completed_at,
                created_at=issue.created_at,
                resolved_at=issue.resolved_at,
                sla_status=sla,
            )
        )

    return result

@router.get("/issues/{issue_id}", response_model=PublicIssueDetail)
def get_public_issue_detail(
    issue_id: str,
    db: Session = Depends(get_db),
):
    """
    Returns detailed sanitized projection of an issue for public inspection.
    Includes before & after photographs, cost breakdown where approved, and AI observations.
    Strictly masks citizen phone numbers, emails, and exact home pins.
    """
    issue = db.query(Issue).filter(Issue.id == issue_id, Issue.status != "DRAFT").first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    loc = issue.locality_unit
    v_name = None
    w_name = None
    if loc:
        if loc.unit_type in ("village", "gram_panchayat"):
            v_name = loc.name_en
        elif loc.unit_type == "ward":
            w_name = loc.name_en
            if loc.parent:
                v_name = loc.parent.name_en

    gen_lat = round(issue.public_latitude or issue.latitude, 3) if (issue.public_latitude or issue.latitude) else None
    gen_lng = round(issue.public_longitude or issue.longitude, 3) if (issue.public_longitude or issue.longitude) else None
    submissions_count = db.query(Submission).filter(Submission.issue_id == issue.id).count()

    sub = db.query(Submission).filter(Submission.issue_id == issue.id).order_by(Submission.created_at.asc()).first()
    sub_desc = sub.description if sub else None

    has_consent = bool(issue.public_display_consent or (sub and sub.public_display_consent))
    if has_consent and sub and sub.reporter and sub.reporter.full_name:
        reporter_name = sub.reporter.full_name
    else:
        reporter_name = "Verified Citizen"

    worker_name = "Assigned Field Staff" if issue.assigned_worker_id else None

    sla = compute_sla_status(
        created_at=issue.created_at,
        category=issue.category,
        priority=issue.priority,
        current_status=issue.status,
        resolved_at=issue.resolved_at,
    )

    # Before and After media assets
    media_records = (
        db.query(MediaAsset)
        .filter(
            MediaAsset.issue_id == issue.id,
            MediaAsset.is_quarantined == False,
        )
        .all()
    )

    before_photos = [
        PublicMediaItem(
            id=m.id,
            evidence_role=m.evidence_role,
            mime_type=m.mime_type,
            view_url=f"/api/v1/public/media/{m.id}/view",
        )
        for m in media_records if m.evidence_role == "CITIZEN_BEFORE"
    ]

    after_photos = [
        PublicMediaItem(
            id=m.id,
            evidence_role=m.evidence_role,
            mime_type=m.mime_type,
            view_url=f"/api/v1/public/media/{m.id}/view",
        )
        for m in media_records if m.evidence_role == "WORKER_AFTER"
    ]

    thumbnail_url = before_photos[0].view_url if before_photos else None
    after_thumbnail_url = after_photos[0].view_url if after_photos else None

    # Fetch AI analysis summary
    ai_rec = (
        db.query(AIBeforeAfterAnalysis)
        .filter(AIBeforeAfterAnalysis.issue_id == issue.id)
        .order_by(AIBeforeAfterAnalysis.created_at.desc())
        .first()
    )
    ai_obs_summary = ai_rec.difference_summary if ai_rec else None
    ai_vis_score = ai_rec.visual_consistency_score if ai_rec else None

    # Timeline with actor details scrubbed to generic official titles
    events = (
        db.query(StatusEvent)
        .filter(StatusEvent.issue_id == issue.id)
        .order_by(StatusEvent.created_at.asc())
        .all()
    )

    timeline: List[PublicTimelineItem] = []
    for ev in events:
        actor_title = "Civic Authority"
        if ev.next_status == "SUBMITTED":
            actor_title = "Citizen Reporter"
        elif ev.next_status in ("ASSIGNED", "UNDER_REVIEW"):
            actor_title = "Panchayat Triage Supervisor"
        elif ev.next_status in ("IN_PROGRESS", "REPAIR_REPORTED"):
            actor_title = "Field Repair Team"
        elif ev.next_status == "RESOLVED":
            actor_title = "Independent Review Supervisor (PDO)"
        elif ev.next_status == "REOPENED":
            actor_title = "Citizen Dispute Review"

        timeline.append(
            PublicTimelineItem(
                status=ev.next_status,
                timestamp=ev.created_at,
                actor_title=actor_title,
                public_summary=ev.reason,
            )
        )

    return PublicIssueDetail(
        id=issue.id,
        reference_number=issue.reference_number,
        category=issue.category,
        status=issue.status,
        priority=issue.priority,
        village_name=v_name,
        ward_name=w_name,
        public_latitude=gen_lat,
        public_longitude=gen_lng,
        submissions_count=max(submissions_count, 1),
        created_at=issue.created_at,
        resolved_at=issue.resolved_at,
        sla_status=sla,
        timeline=timeline,
        approved_media=before_photos + after_photos,
        before_photos=before_photos,
        after_photos=after_photos,
        thumbnail_url=thumbnail_url,
        after_thumbnail_url=after_thumbnail_url,
        has_after_photo=len(after_photos) > 0,
        reporter_display_name=reporter_name,
        assigned_worker_display_name=worker_name,
        estimated_cost=issue.estimated_cost,
        proposed_cost=issue.proposed_cost,
        verified_cost=issue.verified_cost if issue.cost_status == "VERIFIED" else None,
        cost_status=issue.cost_status or "UNRECORDED",
        work_completed_at=issue.work_completed_at,
        work_completion_description=issue.work_completion_description,
        work_performed=issue.work_performed,
        materials_used=issue.materials_used,
        labour_details=issue.labour_details,
        materials_cost=issue.materials_cost if issue.cost_status == "VERIFIED" else None,
        labour_cost=issue.labour_cost if issue.cost_status == "VERIFIED" else None,
        other_expenses_cost=issue.other_expenses_cost if issue.cost_status == "VERIFIED" else None,
        cost_verification_remarks=issue.cost_verification_remarks,
        ai_observation_summary=ai_obs_summary,
        ai_visual_consistency_score=ai_vis_score,
        pdo_officer_title="Village Panchayat Development Officer (PDO)",
        verification_date=issue.resolved_at,
    )

@router.get("/media/{media_id}/view")
def view_public_media(
    media_id: str,
    db: Session = Depends(get_db),
):
    """
    Public media gate:
    Only serves media if is_quarantined is False and parent issue is in a published public status.
    Rejects private or quarantined media with 403 Forbidden.
    """
    media = db.query(MediaAsset).filter(MediaAsset.id == media_id).first()
    if not media:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media asset not found")

    if not media.is_public_approved or media.is_quarantined:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Media asset is private or undergoing moderation review. Public access not approved.",
        )

    # Check parent issue if linked
    if media.issue and media.issue.status == "DRAFT":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Media belongs to an unsubmitted draft report.",
        )

    abs_path = storage_service.get_absolute_path(media.storage_path)
    if not os.path.exists(abs_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media file not found on disk")

    return FileResponse(path=abs_path, media_type=media.mime_type)

@router.get("/analytics", response_model=PublicAnalyticsResponse)
def get_public_analytics(db: Session = Depends(get_db)):
    """
    Ward Accountability Dashboard analytics.
    Accurately computes metrics distinguishing physical Issues vs citizen Submissions.
    """
    all_issues = db.query(Issue).filter(Issue.status != "DRAFT").all()
    total_unique_issues = len(all_issues)
    total_submissions = db.query(Submission).count()

    open_statuses = {"SUBMITTED", "UNDER_REVIEW", "ASSIGNED", "IN_PROGRESS", "NEEDS_INFORMATION"}
    open_issues = sum(1 for i in all_issues if i.status in open_statuses)
    repair_reported_issues = sum(1 for i in all_issues if i.status == "REPAIR_REPORTED")
    resolved_issues = sum(1 for i in all_issues if i.status == "RESOLVED")
    reopened_issues = sum(1 for i in all_issues if i.status == "REOPENED")

    # SLA overdue calculation
    overdue_issues = 0
    resolution_durations = []
    village_counter: Dict[str, Dict[str, int]] = {}
    ward_counter: Dict[str, Dict[str, Any]] = {}
    category_counter: Dict[str, Dict[str, int]] = {}
    department_counter: Dict[str, Dict[str, int]] = {}

    for issue in all_issues:
        sla = compute_sla_status(
            created_at=issue.created_at,
            category=issue.category,
            priority=issue.priority,
            current_status=issue.status,
            resolved_at=issue.resolved_at,
        )
        if sla["is_overdue"]:
            overdue_issues += 1

        if issue.status == "RESOLVED" and issue.resolved_at:
            created = issue.created_at.replace(tzinfo=timezone.utc) if issue.created_at.tzinfo is None else issue.created_at
            resolved = issue.resolved_at.replace(tzinfo=timezone.utc) if issue.resolved_at.tzinfo is None else issue.resolved_at
            hours = max(0.1, (resolved - created).total_seconds() / 3600.0)
            resolution_durations.append(hours)

        # Locality breakdown
        loc = issue.locality_unit
        v_name = "Unassigned Village"
        w_name = "Ward Unknown"
        if loc:
            if loc.unit_type == "village":
                v_name = loc.name_en
            elif loc.unit_type == "ward":
                w_name = loc.name_en
                if loc.parent:
                    v_name = loc.parent.name_en

        # Village
        if v_name not in village_counter:
            village_counter[v_name] = {"total": 0, "resolved": 0, "overdue": 0}
        village_counter[v_name]["total"] += 1
        if issue.status == "RESOLVED":
            village_counter[v_name]["resolved"] += 1
        if sla["is_overdue"]:
            village_counter[v_name]["overdue"] += 1

        # Ward
        if w_name not in ward_counter:
            ward_counter[w_name] = {"village": v_name, "total": 0, "resolved": 0}
        ward_counter[w_name]["total"] += 1
        if issue.status == "RESOLVED":
            ward_counter[w_name]["resolved"] += 1

        # Category
        cat = issue.category
        if cat not in category_counter:
            category_counter[cat] = {"total": 0, "resolved": 0}
        category_counter[cat]["total"] += 1
        if issue.status == "RESOLVED":
            category_counter[cat]["resolved"] += 1

        # Department
        dept_name = issue.department.name_en if issue.department else "General Administration"
        if dept_name not in department_counter:
            department_counter[dept_name] = {"assigned": 0, "resolved": 0}
        department_counter[dept_name]["assigned"] += 1
        if issue.status == "RESOLVED":
            department_counter[dept_name]["resolved"] += 1

    avg_resolution_hours = round(sum(resolution_durations) / len(resolution_durations), 1) if resolution_durations else 0.0

    return PublicAnalyticsResponse(
        total_unique_issues=total_unique_issues,
        total_submissions=total_submissions,
        open_issues=open_issues,
        repair_reported_issues=repair_reported_issues,
        resolved_issues=resolved_issues,
        reopened_issues=reopened_issues,
        overdue_issues=overdue_issues,
        average_resolution_hours=avg_resolution_hours,
        by_village=[
            VillageMetric(
                village_name=v,
                issues_count=stats["total"],
                resolved_count=stats["resolved"],
                overdue_count=stats["overdue"],
            )
            for v, stats in sorted(village_counter.items(), key=lambda x: x[1]["total"], reverse=True)
        ],
        by_ward=[
            WardMetric(
                ward_name=w,
                village_name=stats["village"],
                issues_count=stats["total"],
                resolved_count=stats["resolved"],
            )
            for w, stats in sorted(ward_counter.items(), key=lambda x: x[1]["total"], reverse=True)
        ],
        by_category=[
            CategoryMetric(
                category=cat,
                count=stats["total"],
                resolved_count=stats["resolved"],
            )
            for cat, stats in sorted(category_counter.items(), key=lambda x: x[1]["total"], reverse=True)
        ],
        by_department=[
            DepartmentMetric(
                department_name=d,
                assigned_count=stats["assigned"],
                resolved_count=stats["resolved"],
            )
            for d, stats in sorted(department_counter.items(), key=lambda x: x[1]["assigned"], reverse=True)
        ],
    )

@router.get("/localities", response_model=List[LocalityUnitItem])
def get_public_localities(db: Session = Depends(get_db)):
    """Returns active locality hierarchy (GPs, villages, wards) for public filtering."""
    units = db.query(LocalityUnit).filter(LocalityUnit.is_active == True).order_by(LocalityUnit.name_en.asc()).all()
    return [
        LocalityUnitItem(
            id=u.id,
            unit_type=u.unit_type,
            name_en=u.name_en,
            name_kn=u.name_kn,
            name_hi=u.name_hi,
            parent_id=u.parent_id,
        )
        for u in units
    ]

class PublicMapPoint(BaseModel):
    id: str
    reference_number: str
    category: str
    status: str
    priority: str
    public_latitude: float
    public_longitude: float
    locality_name: Optional[str] = None
    is_recurrence: bool = False
    is_escalated: bool = False

@router.get("/map-data", response_model=List[PublicMapPoint])
def get_public_map_data(
    category: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Returns privacy-sanitized geographic points for village heatmaps and issue mapping (README Section 5.2).
    Uses generalized coordinates (rounded to ~100m); exact private GPS coordinates are never exposed.
    """
    query = db.query(Issue).filter(
        Issue.status.notin_(["DRAFT", "CANCELLED"]),
        (Issue.public_latitude.isnot(None)) | (Issue.latitude.isnot(None)),
    )
    if isinstance(category, str) and category:
        query = query.filter(Issue.category == category)
    if isinstance(status_filter, str) and status_filter:
        query = query.filter(Issue.status == status_filter)

    issues = query.all()
    points = []
    for issue in issues:
        lat = round(issue.public_latitude or issue.latitude, 3)
        lng = round(issue.public_longitude or issue.longitude, 3)
        loc_name = issue.locality_unit.name_en if issue.locality_unit else "Ward Unknown"
        points.append(
            PublicMapPoint(
                id=issue.id,
                reference_number=issue.reference_number,
                category=issue.category,
                status=issue.status,
                priority=issue.priority,
                public_latitude=lat,
                public_longitude=lng,
                locality_name=loc_name,
                is_recurrence=issue.is_recurrence,
                is_escalated=issue.is_escalated,
            )
        )
    return points
