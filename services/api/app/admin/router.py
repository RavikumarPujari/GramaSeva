import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.models.users import Profile, RoleAssignment
from app.models.localities import LocalityUnit, Organization, Department
from app.models.issues import Issue, Submission, MediaAsset, StatusEvent, AuditLog, ModelRun
from app.auth.security import hash_password
from app.auth.dependencies import require_roles, get_current_user

router = APIRouter(prefix="/admin", tags=["Super Admin Platform Governance"])

# --- Schemas ---

class SuperAdminOverviewResponse(BaseModel):
    total_villages: int
    total_pdos: int
    total_workers: int
    total_citizens: int
    total_complaints: int
    resolved_complaints: int
    pending_complaints: int
    in_progress_complaints: int
    system_health: str
    timestamp: str

class VillageItem(BaseModel):
    id: str
    official_code: Optional[str] = None
    name_en: str
    name_kn: str
    name_hi: str
    unit_type: str
    parent_id: Optional[str] = None
    parent_name: Optional[str] = None
    is_active: bool
    assigned_pdo_id: Optional[str] = None
    assigned_pdo_name: Optional[str] = None
    assigned_pdo_email: Optional[str] = None
    boundary_geojson: Optional[str] = None
    total_complaints: int = 0
    resolved_complaints: int = 0

class CreateVillageRequest(BaseModel):
    official_code: Optional[str] = None
    name_en: str
    name_kn: Optional[str] = None
    name_hi: Optional[str] = None
    unit_type: str = "gram_panchayat"  # gram_panchayat or village
    parent_id: Optional[str] = None
    boundary_geojson: Optional[str] = None
    assign_pdo_id: Optional[str] = None

class UpdateVillageRequest(BaseModel):
    official_code: Optional[str] = None
    name_en: Optional[str] = None
    name_kn: Optional[str] = None
    name_hi: Optional[str] = None
    is_active: Optional[bool] = None
    boundary_geojson: Optional[str] = None
    assign_pdo_id: Optional[str] = None

class PDOItem(BaseModel):
    id: str
    email: str
    full_name: str
    phone_number: Optional[str] = None
    is_active: bool
    village_id: Optional[str] = None
    village_name: Optional[str] = None
    is_primary: bool = True
    created_at: str

class CreatePDORequest(BaseModel):
    email: str
    password: str
    full_name: str
    phone_number: Optional[str] = None
    village_id: str
    is_primary: bool = True

class UpdateAccountStatusRequest(BaseModel):
    is_active: bool
    reason: Optional[str] = None

class AuditLogItem(BaseModel):
    id: str
    actor_id: Optional[str] = None
    actor_name: Optional[str] = None
    action: str
    target_type: str
    target_id: str
    details: Optional[str] = None
    created_at: str

# --- Endpoints ---

@router.get("/overview", response_model=SuperAdminOverviewResponse)
def get_superadmin_overview(
    current_admin: Profile = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """
    Returns system-wide actual counts from PostgreSQL/SQLite. Real data only.
    """
    # Count Gram Panchayats and villages under Taluk
    taluk = db.query(LocalityUnit).filter(LocalityUnit.unit_type == "taluk").first()
    villages_query = db.query(LocalityUnit).filter(
        LocalityUnit.unit_type.in_(["gram_panchayat", "village"]),
        LocalityUnit.is_active == True,
    )
    if taluk:
        villages_query = villages_query.filter(LocalityUnit.parent_id == taluk.id)
    total_villages = villages_query.count()

    # Count PDO accounts (role == 'reviewer')
    total_pdos = (
        db.query(RoleAssignment)
        .filter(RoleAssignment.role == "reviewer", RoleAssignment.is_active == True)
        .count()
    )

    # Count Workers
    total_workers = (
        db.query(RoleAssignment)
        .filter(RoleAssignment.role == "worker", RoleAssignment.is_active == True)
        .count()
    )

    # Count Citizens
    total_citizens = (
        db.query(RoleAssignment)
        .filter(RoleAssignment.role == "citizen", RoleAssignment.is_active == True)
        .count()
    )

    # Complaints Breakdown
    all_issues = db.query(Issue).filter(Issue.status != "DRAFT").all()
    total_complaints = len(all_issues)
    resolved_complaints = sum(1 for i in all_issues if i.status == "RESOLVED")
    pending_complaints = sum(1 for i in all_issues if i.status in ["SUBMITTED", "UNDER_REVIEW", "NEEDS_INFORMATION"])
    in_progress_complaints = sum(1 for i in all_issues if i.status in ["ASSIGNED", "IN_PROGRESS", "REPAIR_REPORTED"])

    return SuperAdminOverviewResponse(
        total_villages=total_villages,
        total_pdos=total_pdos,
        total_workers=total_workers,
        total_citizens=total_citizens,
        total_complaints=total_complaints,
        resolved_complaints=resolved_complaints,
        pending_complaints=pending_complaints,
        in_progress_complaints=in_progress_complaints,
        system_health="HEALTHY",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

@router.get("/villages", response_model=List[VillageItem])
def list_villages(
    unit_type: Optional[str] = Query(None),
    current_admin: Profile = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """
    Lists all villages/GPs with their assigned primary PDO and verified boundaries.
    """
    taluk = db.query(LocalityUnit).filter(LocalityUnit.unit_type == "taluk").first()
    query = db.query(LocalityUnit).filter(
        LocalityUnit.is_active == True,
        LocalityUnit.unit_type.in_(["gram_panchayat", "village", "taluk"])
    )
    if taluk:
        query = query.filter((LocalityUnit.parent_id == taluk.id) | (LocalityUnit.id == taluk.id))
    if unit_type:
        query = query.filter(LocalityUnit.unit_type == unit_type)
    else:
        # Default to showing gram panchayats / villages under the taluk
        query = query.filter(LocalityUnit.unit_type.in_(["gram_panchayat", "village"]))
    
    units = query.order_by(LocalityUnit.name_en.asc()).all()
    results: List[VillageItem] = []

    for u in units:
        # Find primary PDO assigned to this locality unit
        pdo_asgn = (
            db.query(RoleAssignment)
            .filter(
                RoleAssignment.role == "reviewer",
                RoleAssignment.jurisdiction_unit_id == u.id,
                RoleAssignment.is_active == True,
            )
            .order_by(RoleAssignment.is_primary.desc())
            .first()
        )

        pdo_id = pdo_asgn.profile.id if pdo_asgn and pdo_asgn.profile else None
        pdo_name = pdo_asgn.profile.full_name if pdo_asgn and pdo_asgn.profile else None
        pdo_email = pdo_asgn.profile.email if pdo_asgn and pdo_asgn.profile else None

        # Count complaints in this locality
        complaints_count = db.query(Issue).filter(Issue.locality_unit_id == u.id, Issue.status != "DRAFT").count()
        resolved_count = db.query(Issue).filter(Issue.locality_unit_id == u.id, Issue.status == "RESOLVED").count()

        parent_name = u.parent.name_en if u.parent else None

        results.append(
            VillageItem(
                id=u.id,
                official_code=u.official_code,
                name_en=u.name_en,
                name_kn=u.name_kn or u.name_en,
                name_hi=u.name_hi or u.name_en,
                unit_type=u.unit_type,
                parent_id=u.parent_id,
                parent_name=parent_name,
                is_active=u.is_active,
                assigned_pdo_id=pdo_id,
                assigned_pdo_name=pdo_name,
                assigned_pdo_email=pdo_email,
                boundary_geojson=u.boundary_geojson,
                total_complaints=complaints_count,
                resolved_complaints=resolved_count,
            )
        )

    return results

@router.post("/villages", response_model=VillageItem, status_code=status.HTTP_201_CREATED)
def create_village(
    req: CreateVillageRequest,
    current_admin: Profile = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """
    Creates a new Gram Panchayat or Village record with verified boundaries.
    """
    org = db.query(Organization).first()
    if not org:
        raise HTTPException(status_code=500, detail="Default organization not initialized")

    unit = LocalityUnit(
        organization_id=org.id,
        unit_type=req.unit_type,
        parent_id=req.parent_id,
        official_code=req.official_code or f"GP-KA-{str(uuid.uuid4())[:6].upper()}",
        name_en=req.name_en,
        name_kn=req.name_kn or req.name_en,
        name_hi=req.name_hi or req.name_en,
        boundary_geojson=req.boundary_geojson,
        is_active=True,
    )
    db.add(unit)
    db.flush()

    # Assign PDO if requested
    pdo_name = None
    pdo_email = None
    if req.assign_pdo_id:
        pdo_profile = db.query(Profile).filter(Profile.id == req.assign_pdo_id).first()
        if pdo_profile:
            # Enforce exactly one primary PDO per GP
            db.query(RoleAssignment).filter(
                RoleAssignment.jurisdiction_unit_id == unit.id,
                RoleAssignment.role == "reviewer",
            ).update({"is_primary": False})

            # Check if this profile already has reviewer role
            asgn = db.query(RoleAssignment).filter(
                RoleAssignment.profile_id == pdo_profile.id,
                RoleAssignment.role == "reviewer",
            ).first()
            if asgn:
                asgn.jurisdiction_unit_id = unit.id
                asgn.is_primary = True
                asgn.is_active = True
            else:
                db.add(
                    RoleAssignment(
                        profile_id=pdo_profile.id,
                        role="reviewer",
                        jurisdiction_unit_id=unit.id,
                        is_primary=True,
                        is_active=True,
                    )
                )
            pdo_name = pdo_profile.full_name
            pdo_email = pdo_profile.email

    # Log audit event
    audit = AuditLog(
        actor_profile_id=current_admin.id,
        action="CREATE_VILLAGE",
        target_type="locality_unit",
        target_id=unit.id,
        details_json=f'{{"name": "{unit.name_en}", "code": "{unit.official_code}"}}',
    )
    db.add(audit)
    db.commit()
    db.refresh(unit)

    return VillageItem(
        id=unit.id,
        official_code=unit.official_code,
        name_en=unit.name_en,
        name_kn=unit.name_kn,
        name_hi=unit.name_hi,
        unit_type=unit.unit_type,
        parent_id=unit.parent_id,
        is_active=unit.is_active,
        assigned_pdo_id=req.assign_pdo_id,
        assigned_pdo_name=pdo_name,
        assigned_pdo_email=pdo_email,
        boundary_geojson=unit.boundary_geojson,
        total_complaints=0,
        resolved_complaints=0,
    )

@router.patch("/villages/{village_id}", response_model=VillageItem)
def update_village(
    village_id: str,
    req: UpdateVillageRequest,
    current_admin: Profile = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """
    Updates village record, jurisdiction boundary, or reassigns primary PDO.
    """
    unit = db.query(LocalityUnit).filter(LocalityUnit.id == village_id).first()
    if not unit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Village not found")

    if req.name_en is not None:
        unit.name_en = req.name_en
    if req.name_kn is not None:
        unit.name_kn = req.name_kn
    if req.name_hi is not None:
        unit.name_hi = req.name_hi
    if req.official_code is not None:
        unit.official_code = req.official_code
    if req.is_active is not None:
        unit.is_active = req.is_active
    if req.boundary_geojson is not None:
        unit.boundary_geojson = req.boundary_geojson

    pdo_id = None
    pdo_name = None
    pdo_email = None

    if req.assign_pdo_id is not None:
        if req.assign_pdo_id == "":
            # Unassign current PDO
            db.query(RoleAssignment).filter(
                RoleAssignment.jurisdiction_unit_id == unit.id,
                RoleAssignment.role == "reviewer",
            ).update({"jurisdiction_unit_id": None, "is_primary": False})
        else:
            pdo_profile = db.query(Profile).filter(Profile.id == req.assign_pdo_id).first()
            if not pdo_profile:
                raise HTTPException(status_code=404, detail="PDO profile not found")

            # Demote any prior primary PDO on this GP
            db.query(RoleAssignment).filter(
                RoleAssignment.jurisdiction_unit_id == unit.id,
                RoleAssignment.role == "reviewer",
            ).update({"is_primary": False})

            # Assign new primary PDO
            asgn = db.query(RoleAssignment).filter(
                RoleAssignment.profile_id == pdo_profile.id,
                RoleAssignment.role == "reviewer",
            ).first()
            if asgn:
                asgn.jurisdiction_unit_id = unit.id
                asgn.is_primary = True
                asgn.is_active = True
            else:
                db.add(
                    RoleAssignment(
                        profile_id=pdo_profile.id,
                        role="reviewer",
                        jurisdiction_unit_id=unit.id,
                        is_primary=True,
                        is_active=True,
                    )
                )
            pdo_id = pdo_profile.id
            pdo_name = pdo_profile.full_name
            pdo_email = pdo_profile.email

    audit = AuditLog(
        actor_profile_id=current_admin.id,
        action="UPDATE_VILLAGE",
        target_type="locality_unit",
        target_id=unit.id,
        details_json=f'{{"name": "{unit.name_en}"}}',
    )
    db.add(audit)
    db.commit()
    db.refresh(unit)

    complaints_count = db.query(Issue).filter(Issue.locality_unit_id == unit.id, Issue.status != "DRAFT").count()
    resolved_count = db.query(Issue).filter(Issue.locality_unit_id == unit.id, Issue.status == "RESOLVED").count()

    return VillageItem(
        id=unit.id,
        official_code=unit.official_code,
        name_en=unit.name_en,
        name_kn=unit.name_kn,
        name_hi=unit.name_hi,
        unit_type=unit.unit_type,
        parent_id=unit.parent_id,
        is_active=unit.is_active,
        assigned_pdo_id=pdo_id,
        assigned_pdo_name=pdo_name,
        assigned_pdo_email=pdo_email,
        boundary_geojson=unit.boundary_geojson,
        total_complaints=complaints_count,
        resolved_complaints=resolved_count,
    )

@router.get("/pdos", response_model=List[PDOItem])
def list_pdos(
    current_admin: Profile = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """
    Lists all Village PDO accounts and their assigned Gram Panchayat.
    """
    assignments = (
        db.query(RoleAssignment, Profile)
        .join(Profile, RoleAssignment.profile_id == Profile.id)
        .filter(RoleAssignment.role == "reviewer")
        .all()
    )

    results: List[PDOItem] = []
    for asgn, prof in assignments:
        v_name = None
        if asgn.jurisdiction_unit_id:
            unit = db.query(LocalityUnit).filter(LocalityUnit.id == asgn.jurisdiction_unit_id).first()
            if unit:
                v_name = unit.name_en

        results.append(
            PDOItem(
                id=prof.id,
                email=prof.email,
                full_name=prof.full_name,
                phone_number=prof.phone_number,
                is_active=prof.is_active and asgn.is_active,
                village_id=asgn.jurisdiction_unit_id,
                village_name=v_name,
                is_primary=getattr(asgn, "is_primary", True),
                created_at=prof.created_at.isoformat() if prof.created_at else datetime.now(timezone.utc).isoformat(),
            )
        )

    return results

@router.post("/pdos", response_model=PDOItem, status_code=status.HTTP_201_CREATED)
def create_pdo_account(
    req: CreatePDORequest,
    current_admin: Profile = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """
    Creates a new PDO account and assigns exactly one primary PDO to the specified Gram Panchayat.
    """
    existing = db.query(Profile).filter(Profile.email == req.email.lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists.",
        )

    village = db.query(LocalityUnit).filter(LocalityUnit.id == req.village_id).first()
    if not village:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Selected Gram Panchayat or Village not found.",
        )

    # Enforce exactly one primary PDO per village
    if req.is_primary:
        db.query(RoleAssignment).filter(
            RoleAssignment.jurisdiction_unit_id == village.id,
            RoleAssignment.role == "reviewer",
        ).update({"is_primary": False})

    profile = Profile(
        email=req.email.lower(),
        password_hash=hash_password(req.password),
        full_name=req.full_name,
        phone_number=req.phone_number,
        preferred_locale="en",
        is_active=True,
    )
    db.add(profile)
    db.flush()

    role_asgn = RoleAssignment(
        profile_id=profile.id,
        role="reviewer",
        jurisdiction_unit_id=village.id,
        is_primary=req.is_primary,
        is_active=True,
        approval_status="APPROVED",
    )
    db.add(role_asgn)

    audit = AuditLog(
        actor_profile_id=current_admin.id,
        action="CREATE_PDO_ACCOUNT",
        target_type="profile",
        target_id=profile.id,
        details_json=f'{{"email": "{profile.email}", "village": "{village.name_en}"}}',
    )
    db.add(audit)
    db.commit()
    db.refresh(profile)

    return PDOItem(
        id=profile.id,
        email=profile.email,
        full_name=profile.full_name,
        phone_number=profile.phone_number,
        is_active=profile.is_active,
        village_id=village.id,
        village_name=village.name_en,
        is_primary=req.is_primary,
        created_at=profile.created_at.isoformat(),
    )

@router.patch("/pdos/{profile_id}/status")
def update_pdo_status(
    profile_id: str,
    req: UpdateAccountStatusRequest,
    current_admin: Profile = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """
    Activates, suspends, or deactivates a PDO account.
    """
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="PDO profile not found")

    profile.is_active = req.is_active
    db.query(RoleAssignment).filter(RoleAssignment.profile_id == profile_id).update({"is_active": req.is_active})

    action = "ACTIVATE_PDO" if req.is_active else "SUSPEND_PDO"
    reason_str = req.reason or "Administrative action"
    audit = AuditLog(
        actor_profile_id=current_admin.id,
        action=action,
        target_type="profile",
        target_id=profile.id,
        details_json=f'{{"is_active": {req.is_active}, "reason": "{reason_str}"}}',
    )
    db.add(audit)
    db.commit()

    return {"status": "success", "profile_id": profile.id, "is_active": profile.is_active}

@router.get("/audit-logs", response_model=List[AuditLogItem])
def get_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    current_admin: Profile = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """
    Returns audit log records for privileged administrative actions.
    """
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
    results = []
    for l in logs:
        actor_name = None
        if l.actor_profile_id:
            actor = db.query(Profile.full_name).filter(Profile.id == l.actor_profile_id).first()
            actor_name = actor[0] if actor else None
        results.append(
            AuditLogItem(
                id=l.id,
                actor_id=l.actor_profile_id,
                actor_name=actor_name,
                action=l.action,
                target_type=l.target_type,
                target_id=l.target_id,
                details=l.details_json,
                created_at=l.created_at.isoformat() if l.created_at else datetime.now(timezone.utc).isoformat(),
            )
        )
    return results

@router.get("/system-health")
def get_system_health(
    current_admin: Profile = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """
    System monitoring metrics for API, DB, and AI models.
    """
    # Check DB
    db_ok = True
    try:
        db.execute(func.now()).scalar()
    except Exception:
        db_ok = False

    # Check AI Model Runs
    total_model_runs = db.query(ModelRun).count()
    failed_model_runs = db.query(ModelRun).filter(ModelRun.status == "FAILED").count()

    return {
        "status": "HEALTHY" if db_ok else "DEGRADED",
        "database": "CONNECTED" if db_ok else "ERROR",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_model_runs": total_model_runs,
        "failed_model_runs": failed_model_runs,
        "environment": "production",
    }

# --- Section 3: Taluk Analytics & Announcements ---

class CreateAnnouncementRequest(BaseModel):
    title: str
    content: str
    target_type: str  # ALL_PDOS, SELECTED_VILLAGES, INDIVIDUAL_PDO
    target_village_ids: Optional[List[str]] = None
    target_pdo_id: Optional[str] = None

@router.get("/taluk-analytics")
def get_taluk_analytics(
    current_admin: Profile = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """
    Consolidated Taluk & City Level Analytics for Super Admin.
    Zero fake statistics; computed directly from database records.
    """
    total_complaints = db.query(Issue).count()
    pending = db.query(Issue).filter(Issue.status.in_(["SUBMITTED", "UNDER_REVIEW"])).count()
    in_progress = db.query(Issue).filter(Issue.status.in_(["ASSIGNED", "IN_PROGRESS", "REPAIR_REPORTED"])).count()
    resolved = db.query(Issue).filter(Issue.status == "RESOLVED").count()
    high_priority = db.query(Issue).filter(Issue.priority.in_(["HIGH", "CRITICAL"])).count()

    # Category distribution
    cat_counts = (
        db.query(Issue.category, func.count(Issue.id))
        .group_by(Issue.category)
        .all()
    )
    category_dist = {cat: count for cat, count in cat_counts}

    # Status distribution
    status_counts = (
        db.query(Issue.status, func.count(Issue.id))
        .group_by(Issue.status)
        .all()
    )
    status_dist = {st: count for st, count in status_counts}

    # Villages comparison under Belagavi Taluk
    taluk = db.query(LocalityUnit).filter(LocalityUnit.unit_type == "taluk").first()
    taluk_name = taluk.name_en if taluk else "Belagavi Taluk"

    villages_query = db.query(LocalityUnit).filter(
        LocalityUnit.is_active == True,
        LocalityUnit.unit_type.in_(["gram_panchayat", "village"])
    )
    if taluk:
        villages_query = villages_query.filter(LocalityUnit.parent_id == taluk.id)
    villages = villages_query.order_by(LocalityUnit.name_en.asc()).all()

    village_comp = []
    unassigned_villages = []
    
    for v in villages:
        total_v = db.query(Issue).filter(Issue.locality_unit_id == v.id).count()
        res_v = db.query(Issue).filter(Issue.locality_unit_id == v.id, Issue.status == "RESOLVED").count()
        pend_v = db.query(Issue).filter(Issue.locality_unit_id == v.id, Issue.status.in_(["SUBMITTED", "UNDER_REVIEW"])).count()
        hi_v = db.query(Issue).filter(Issue.locality_unit_id == v.id, Issue.priority.in_(["HIGH", "CRITICAL"])).count()

        # Find primary PDO
        pdo_role = (
            db.query(RoleAssignment)
            .filter(
                RoleAssignment.jurisdiction_unit_id == v.id,
                RoleAssignment.role.in_(["reviewer", "pdo"]),
                RoleAssignment.is_active == True,
            )
            .first()
        )
        pdo_name = None
        if pdo_role:
            pdo_p = db.query(Profile.full_name).filter(Profile.id == pdo_role.profile_id).first()
            pdo_name = pdo_p[0] if pdo_p else None
        else:
            unassigned_villages.append({"id": v.id, "name_en": v.name_en})

        village_comp.append({
            "id": v.id,
            "name_en": v.name_en,
            "unit_type": v.unit_type,
            "issues_count": total_v,
            "resolved_count": res_v,
            "pending_count": pend_v,
            "high_priority_count": hi_v,
            "assigned_pdo_name": pdo_name,
            "has_pdo": pdo_name is not None,
        })

    # Top villages by pending complaints
    top_pending = sorted(village_comp, key=lambda x: x["pending_count"], reverse=True)[:5]
    total_villages_count = len(villages)
    covered_villages_count = total_villages_count - len(unassigned_villages)
    cov_pct = round((covered_villages_count / total_villages_count * 100), 1) if total_villages_count > 0 else 0.0

    return {
        "taluk_name": taluk_name,
        "total_complaints": total_complaints,
        "pending": pending,
        "in_progress": in_progress,
        "resolved": resolved,
        "high_priority": high_priority,
        "category_distribution": category_dist,
        "status_distribution": status_dist,
        "village_comparison": village_comp,
        "top_pending_villages": top_pending,
        "unassigned_villages": unassigned_villages,
        "pdo_coverage": {
            "total_villages": total_villages_count,
            "covered_villages": covered_villages_count,
            "unassigned_villages": len(unassigned_villages),
            "coverage_percent": cov_pct,
        },
    }

@router.post("/announcements")
def create_announcement(
    req: CreateAnnouncementRequest,
    current_admin: Profile = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """
    Broadcast or targeted announcement from Super Admin to Village PDOs.
    Persists announcement and writes in-app notifications for each target PDO.
    """
    from app.models.users import Announcement
    from app.models.issues import Notification
    import json

    recipient_profile_ids = set()

    if req.target_type == "ALL_PDOS":
        pdos = (
            db.query(RoleAssignment.profile_id)
            .filter(RoleAssignment.role.in_(["reviewer", "pdo"]), RoleAssignment.is_active == True)
            .distinct()
            .all()
        )
        for p in pdos:
            recipient_profile_ids.add(p[0])

    elif req.target_type == "SELECTED_VILLAGES" and req.target_village_ids:
        pdos = (
            db.query(RoleAssignment.profile_id)
            .filter(
                RoleAssignment.role.in_(["reviewer", "pdo"]),
                RoleAssignment.jurisdiction_unit_id.in_(req.target_village_ids),
                RoleAssignment.is_active == True,
            )
            .all()
        )
        for p in pdos:
            recipient_profile_ids.add(p[0])

    elif req.target_type == "INDIVIDUAL_PDO" and req.target_pdo_id:
        recipient_profile_ids.add(req.target_pdo_id)

    # Create Announcement record
    ann_id = str(uuid.uuid4())
    ann = Announcement(
        id=ann_id,
        sender_id=current_admin.id,
        title=req.title,
        content=req.content,
        target_type=req.target_type,
        target_village_ids=json.dumps(req.target_village_ids) if req.target_village_ids else None,
        target_pdo_id=req.target_pdo_id,
        delivered_count=len(recipient_profile_ids),
    )
    db.add(ann)

    # Deliver Notification to each target PDO
    for pid in recipient_profile_ids:
        notif = Notification(
            id=str(uuid.uuid4()),
            profile_id=pid,
            event_type="ANNOUNCEMENT",
            title=f"Taluk Announcement: {req.title}",
            message=req.content,
            locale="en",
            dedup_key=f"ann_{ann_id}_{pid}",
            is_read=False,
        )
        db.add(notif)

    # Record in AuditLog
    audit = AuditLog(
        id=str(uuid.uuid4()),
        actor_profile_id=current_admin.id,
        action="ANNOUNCEMENT_BROADCAST",
        target_type="ANNOUNCEMENT",
        target_id=ann_id,
        details_json=f'{{"title": "{req.title}", "target_type": "{req.target_type}", "delivered_count": {len(recipient_profile_ids)}}}',
    )
    db.add(audit)
    db.commit()

    return {
        "status": "success",
        "id": ann_id,
        "title": req.title,
        "target_type": req.target_type,
        "delivered_count": len(recipient_profile_ids),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

@router.get("/announcements")
def get_announcements(
    current_admin: Profile = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """
    History of administrative announcements sent across the Taluk.
    """
    from app.models.users import Announcement
    anns = db.query(Announcement).order_by(Announcement.created_at.desc()).limit(50).all()
    results = []
    for a in anns:
        results.append({
            "id": a.id,
            "title": a.title,
            "content": a.content,
            "target_type": a.target_type,
            "target_village_ids": a.target_village_ids,
            "target_pdo_id": a.target_pdo_id,
            "delivered_count": a.delivered_count,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        })
    return results

@router.get("/users")
def get_user_management_roster(
    role: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50,
    current_admin: Profile = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """
    Complete user roster with role assignments and village affiliations.
    """
    query = db.query(Profile)
    if search:
        s = f"%{search.lower()}%"
        query = query.filter(Profile.email.ilike(s) | Profile.full_name.ilike(s))

    profiles = query.limit(limit).all()
    results = []
    for p in profiles:
        assignments = (
            db.query(RoleAssignment)
            .filter(RoleAssignment.profile_id == p.id, RoleAssignment.is_active == True)
            .all()
        )
        user_roles = [a.role for a in assignments]
        if role and role.lower() not in [r.lower() for r in user_roles]:
            continue

        jur_names = []
        for a in assignments:
            if a.jurisdiction_unit_id:
                u = db.query(LocalityUnit.name_en).filter(LocalityUnit.id == a.jurisdiction_unit_id).first()
                if u:
                    jur_names.append(u[0])

        results.append({
            "id": p.id,
            "full_name": p.full_name,
            "email": p.email,
            "phone_number": p.phone_number,
            "is_active": p.is_active,
            "roles": user_roles,
            "jurisdictions": jur_names,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        })
    return results
