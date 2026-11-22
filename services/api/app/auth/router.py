import os
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from app.core.database import get_db
from app.core.config import settings
from app.models.users import Profile, RoleAssignment
from app.models.localities import LocalityUnit
from app.auth.security import hash_password, verify_password, create_access_token
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication & Profiles"])

class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    phone_number: Optional[str] = None
    preferred_locale: Optional[str] = "en"

class RegisterWorkerRequest(BaseModel):
    email: str
    password: str
    full_name: str
    phone_number: Optional[str] = None
    preferred_locale: Optional[str] = "en"
    village_id: str
    department_id: Optional[str] = None

class LoginRequest(BaseModel):
    email: str
    password: str
    selected_role: Optional[str] = None

class DemoSessionRequest(BaseModel):
    role: str

class RoleInfo(BaseModel):
    role: str
    jurisdiction_unit_id: Optional[str] = None
    jurisdiction_name: Optional[str] = None
    department_id: Optional[str] = None
    approval_status: Optional[str] = "APPROVED"
    is_primary: Optional[bool] = False

class ProfileResponse(BaseModel):
    id: str
    email: str
    full_name: str
    preferred_locale: str
    taluk: Optional[str] = "Belagavi Taluk"
    roles: List[RoleInfo]
    is_approved: bool = True
    approval_status: str = "APPROVED"

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    profile: ProfileResponse

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(Profile).filter(Profile.email == req.email.lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists",
        )
    
    if len(req.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters long",
        )

    profile = Profile(
        email=req.email.lower(),
        password_hash=hash_password(req.password),
        full_name=req.full_name,
        phone_number=req.phone_number,
        preferred_locale=req.preferred_locale or "en",
    )
    db.add(profile)
    db.flush()

    # Assign default citizen role
    citizen_role = RoleAssignment(
        profile_id=profile.id,
        role="citizen",
        is_active=True,
        approval_status="APPROVED",
    )
    db.add(citizen_role)
    db.commit()
    db.refresh(profile)

    token = create_access_token({"sub": profile.id, "email": profile.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "profile": {
            "id": profile.id,
            "email": profile.email,
            "full_name": profile.full_name,
            "preferred_locale": profile.preferred_locale,
            "roles": [{"role": "citizen", "approval_status": "APPROVED", "is_primary": False}],
            "is_approved": True,
            "approval_status": "APPROVED",
        },
    }

@router.post("/register-worker", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_worker(req: RegisterWorkerRequest, db: Session = Depends(get_db)):
    """Public worker registration. Account remains PENDING until Village PDO approves."""
    existing = db.query(Profile).filter(Profile.email == req.email.lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists",
        )
    
    if len(req.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters long",
        )

    # Verify village exists
    village = db.query(LocalityUnit).filter(LocalityUnit.id == req.village_id).first()
    if not village:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Selected village / Gram Panchayat not found",
        )

    profile = Profile(
        email=req.email.lower(),
        password_hash=hash_password(req.password),
        full_name=req.full_name,
        phone_number=req.phone_number,
        preferred_locale=req.preferred_locale or "en",
    )
    db.add(profile)
    db.flush()

    worker_role = RoleAssignment(
        profile_id=profile.id,
        role="worker",
        jurisdiction_unit_id=req.village_id,
        department_id=req.department_id,
        is_active=True,
        approval_status="PENDING",
    )
    db.add(worker_role)
    db.commit()
    db.refresh(profile)

    token = create_access_token({"sub": profile.id, "email": profile.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "profile": {
            "id": profile.id,
            "email": profile.email,
            "full_name": profile.full_name,
            "preferred_locale": profile.preferred_locale,
            "roles": [
                RoleInfo(
                    role="worker",
                    jurisdiction_unit_id=req.village_id,
                    jurisdiction_name=village.name_en,
                    department_id=req.department_id,
                    approval_status="PENDING",
                    is_primary=False,
                )
            ],
            "is_approved": False,
            "approval_status": "PENDING",
        },
    }

@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    clean_identifier = " ".join(req.email.strip().split())
    
    # 1. First attempt exact or lowercase email lookup
    profile = db.query(Profile).filter(Profile.email == clean_identifier.lower()).first()

    # 2. Phone number lookup (if user typed their 10-digit mobile number)
    if not profile:
        digits_only = "".join(ch for ch in clean_identifier if ch.isdigit())
        if len(digits_only) >= 10:
            last10 = digits_only[-10:]
            profile = db.query(Profile).filter(Profile.phone_number.ilike(f"%{last10}%")).first()

    # 3. Full name lookup (case-insensitive)
    if not profile:
        matched_profiles = (
            db.query(Profile)
            .filter(func.lower(func.trim(Profile.full_name)) == clean_identifier.lower())
            .all()
        )
        if len(matched_profiles) == 1:
            profile = matched_profiles[0]
        elif len(matched_profiles) > 1:
            # Prefer profile with active staff/reviewer roles if available
            staff_profile = next((p for p in matched_profiles if any(ra.role in ["admin", "reviewer", "pdo", "worker"] for ra in p.role_assignments)), None)
            profile = staff_profile or matched_profiles[0]

    if not profile or not verify_password(req.password, profile.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. Please verify your login identifier and password.",
        )
    
    if not profile.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Please contact your administrator.",
        )

    roles_data: List[RoleInfo] = []
    assignments = (
        db.query(RoleAssignment)
        .filter(RoleAssignment.profile_id == profile.id, RoleAssignment.is_active == True)
        .all()
    )

    active_role_names = [a.role.lower() for a in assignments]
    
    # Normalize roles into authorized capabilities
    normalized_capabilities = set()
    for r in active_role_names:
        if r in ("admin", "super_admin", "superadmin"):
            normalized_capabilities.update(["admin", "reviewer", "citizen"])
        elif r in ("reviewer", "pdo", "village_pdo"):
            normalized_capabilities.update(["reviewer", "citizen"])
        elif r in ("worker", "field_worker"):
            normalized_capabilities.update(["worker", "citizen"])
        elif r == "citizen":
            normalized_capabilities.add("citizen")
        else:
            normalized_capabilities.add(r)
    
    # Every verified profile in GramaSeva is authorized for citizen portal access
    normalized_capabilities.add("citizen")

    # Validate Selected Role Access Control
    if req.selected_role:
        role_mapping = {
            "super_admin": "admin",
            "superadmin": "admin",
            "admin": "admin",
            "village_pdo": "reviewer",
            "pdo": "reviewer",
            "reviewer": "reviewer",
            "worker": "worker",
            "citizen": "citizen",
        }
        expected_role = role_mapping.get(req.selected_role.lower(), req.selected_role.lower())
        
        has_role = expected_role in normalized_capabilities
        if not has_role:
            role_display_names = {
                "admin": "Super Admin",
                "reviewer": "Village PDO",
                "worker": "Worker",
                "citizen": "Citizen",
            }
            display_expected = role_display_names.get(expected_role, expected_role)
            actual_role_display = "Citizen"
            if "admin" in normalized_capabilities:
                actual_role_display = "Super Admin"
            elif "reviewer" in normalized_capabilities:
                actual_role_display = "Village PDO"
            elif "worker" in normalized_capabilities:
                actual_role_display = "Worker"
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: This account is registered as a {actual_role_display}. Please select '{actual_role_display}' on the login screen to sign in.",
            )

    overall_approval_status = "APPROVED"
    is_approved = True

    for a in assignments:
        jur_name = None
        if a.jurisdiction_unit_id:
            unit = db.query(LocalityUnit).filter(LocalityUnit.id == a.jurisdiction_unit_id).first()
            if unit:
                jur_name = unit.name_en
        
        appr_status = getattr(a, "approval_status", "APPROVED") or "APPROVED"
        is_prim = getattr(a, "is_primary", False) or False

        if a.role == "worker" and appr_status != "APPROVED":
            overall_approval_status = appr_status
            is_approved = False

        roles_data.append(
            RoleInfo(
                role=a.role,
                jurisdiction_unit_id=a.jurisdiction_unit_id,
                jurisdiction_name=jur_name,
                department_id=a.department_id,
                approval_status=appr_status,
                is_primary=is_prim,
            )
        )

    token = create_access_token({"sub": profile.id, "email": profile.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "profile": {
            "id": profile.id,
            "email": profile.email,
            "full_name": profile.full_name,
            "preferred_locale": profile.preferred_locale,
            "taluk": getattr(profile, "taluk", "Belagavi Taluk") or "Belagavi Taluk",
            "roles": roles_data,
            "is_approved": is_approved,
            "approval_status": overall_approval_status,
        },
    }

@router.get("/me", response_model=ProfileResponse)
def get_my_profile(
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assignments = (
        db.query(RoleAssignment)
        .filter(RoleAssignment.profile_id == current_user.id, RoleAssignment.is_active == True)
        .all()
    )
    roles_data = []
    overall_approval_status = "APPROVED"
    is_approved = True

    for a in assignments:
        jur_name = None
        if a.jurisdiction_unit_id:
            unit = db.query(LocalityUnit).filter(LocalityUnit.id == a.jurisdiction_unit_id).first()
            if unit:
                jur_name = unit.name_en
        
        appr_status = getattr(a, "approval_status", "APPROVED") or "APPROVED"
        is_prim = getattr(a, "is_primary", False) or False

        if a.role == "worker" and appr_status != "APPROVED":
            overall_approval_status = appr_status
            is_approved = False

        roles_data.append(
            RoleInfo(
                role=a.role,
                jurisdiction_unit_id=a.jurisdiction_unit_id,
                jurisdiction_name=jur_name,
                department_id=a.department_id,
                approval_status=appr_status,
                is_primary=is_prim,
            )
        )

    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "preferred_locale": current_user.preferred_locale,
        "taluk": getattr(current_user, "taluk", "Belagavi Taluk") or "Belagavi Taluk",
        "roles": roles_data,
        "is_approved": is_approved,
        "approval_status": overall_approval_status,
    }


def _check_demo_access_allowed():
    app_env = (os.getenv("APP_ENV") or settings.app_env or "development").strip().lower()
    demo_enabled = (
        os.getenv("ALLOW_DEMO_LOGIN", "").strip().lower() in ("true", "1", "yes")
        or os.getenv("HACKATHON_DEMO_MODE", "").strip().lower() in ("true", "1", "yes")
    )
    if app_env == "production" and not demo_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="One-click demo access is disabled in production environments. Please use standard authentication.",
        )


def _create_demo_session_for_profile(profile: Profile, db: Session) -> dict:
    assignments = (
        db.query(RoleAssignment)
        .filter(RoleAssignment.profile_id == profile.id, RoleAssignment.is_active == True)
        .all()
    )

    roles_data: List[RoleInfo] = []
    overall_approval_status = "APPROVED"
    is_approved = True

    for a in assignments:
        jur_name = None
        if a.jurisdiction_unit_id:
            unit = db.query(LocalityUnit).filter(LocalityUnit.id == a.jurisdiction_unit_id).first()
            if unit:
                jur_name = unit.name_en

        appr_status = getattr(a, "approval_status", "APPROVED") or "APPROVED"
        is_prim = getattr(a, "is_primary", False) or False

        roles_data.append(
            RoleInfo(
                role=a.role,
                jurisdiction_unit_id=a.jurisdiction_unit_id,
                jurisdiction_name=jur_name,
                department_id=a.department_id,
                approval_status=appr_status,
                is_primary=is_prim,
            )
        )

    token = create_access_token({"sub": profile.id, "email": profile.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "profile": {
            "id": profile.id,
            "email": profile.email,
            "full_name": profile.full_name,
            "preferred_locale": profile.preferred_locale,
            "taluk": getattr(profile, "taluk", "Belagavi Taluk") or "Belagavi Taluk",
            "roles": roles_data,
            "is_approved": is_approved,
            "approval_status": overall_approval_status,
        },
    }


@router.post("/dev-admin-session", response_model=TokenResponse)
@router.get("/dev-admin-session", response_model=TokenResponse)
def dev_admin_session(db: Session = Depends(get_db)):
    """
    Demo/Development one-click access: Automatically creates a valid authenticated
    session for the official Super Admin (Ravikumar - admin@fixproof.org).
    Strictly blocked in production environments unless demo mode is explicitly enabled.
    """
    _check_demo_access_allowed()
    profile = db.query(Profile).filter(Profile.email == "admin@fixproof.org").first()
    if not profile:
        profile = (
            db.query(Profile)
            .join(RoleAssignment, RoleAssignment.profile_id == Profile.id)
            .filter(RoleAssignment.role == "admin", RoleAssignment.is_active == True, Profile.is_active == True)
            .first()
        )
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Super Admin account not found in the database. Please ensure initial administrative setup is complete.",
        )
    return _create_demo_session_for_profile(profile, db)


@router.post("/dev-pdo-session", response_model=TokenResponse)
@router.get("/dev-pdo-session", response_model=TokenResponse)
def dev_pdo_session(db: Session = Depends(get_db)):
    """
    Demo/Development one-click access: Automatically creates a valid authenticated
    session for the official Village PDO (Basavaraj Patil - pdo.peeranwadi@belagavi.gov.in).
    Strictly blocked in production environments unless demo mode is explicitly enabled.
    """
    _check_demo_access_allowed()

    # 1. Locate canonical Peeranwadi PDO account
    profile = db.query(Profile).filter(Profile.email == "pdo.peeranwadi@belagavi.gov.in").first()

    # 2. Resilient fallback to any active reviewer profile if canonical was modified
    if not profile:
        profile = (
            db.query(Profile)
            .join(RoleAssignment, RoleAssignment.profile_id == Profile.id)
            .filter(RoleAssignment.role == "reviewer", RoleAssignment.is_active == True, Profile.is_active == True)
            .first()
        )

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Village PDO account not found in the database. Please ensure initial administrative setup is complete.",
        )

    return _create_demo_session_for_profile(profile, db)


@router.post("/dev-worker-session", response_model=TokenResponse)
@router.get("/dev-worker-session", response_model=TokenResponse)
def dev_worker_session(db: Session = Depends(get_db)):
    """
    Demo/Development one-click access: Automatically creates a valid authenticated
    session for the official Field Worker (Ramesh K. - worker.ramesh@fixproof.org).
    Strictly blocked in production environments unless demo mode is explicitly enabled.
    """
    _check_demo_access_allowed()
    profile = db.query(Profile).filter(Profile.email == "worker.ramesh@fixproof.org").first()
    if not profile:
        profile = (
            db.query(Profile)
            .join(RoleAssignment, RoleAssignment.profile_id == Profile.id)
            .filter(RoleAssignment.role == "worker", RoleAssignment.is_active == True, Profile.is_active == True)
            .first()
        )
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker account not found in the database. Please ensure initial administrative setup is complete.",
        )
    return _create_demo_session_for_profile(profile, db)


@router.post("/dev-citizen-session", response_model=TokenResponse)
@router.get("/dev-citizen-session", response_model=TokenResponse)
def dev_citizen_session(db: Session = Depends(get_db)):
    """
    Demo/Development one-click access: Automatically creates a valid authenticated
    session for the verified Citizen demo account (citizen.ananya@example.com - Ananya Sharma).
    Strictly blocked in production environments unless demo mode is explicitly enabled.
    """
    _check_demo_access_allowed()
    profile = db.query(Profile).filter(Profile.email == "citizen.ananya@example.com").first()
    if not profile:
        profile = (
            db.query(Profile)
            .join(RoleAssignment, RoleAssignment.profile_id == Profile.id)
            .filter(RoleAssignment.role == "citizen", RoleAssignment.is_active == True, Profile.is_active == True)
            .first()
        )
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Citizen demo account not found in database.",
        )
    return _create_demo_session_for_profile(profile, db)


@router.post("/demo-session", response_model=TokenResponse)
def demo_session(req: DemoSessionRequest, db: Session = Depends(get_db)):
    """
    Unified Hackathon demo session access for judges and evaluators.
    Safely routes to the designated demo profile for super_admin, village_pdo, worker, or citizen.
    """
    role_clean = req.role.strip().lower()
    if role_clean in ("super_admin", "admin", "administrator"):
        return dev_admin_session(db)
    elif role_clean in ("village_pdo", "pdo", "reviewer"):
        return dev_pdo_session(db)
    elif role_clean in ("worker", "field_worker"):
        return dev_worker_session(db)
    elif role_clean in ("citizen", "resident"):
        return dev_citizen_session(db)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported demo role. Allowed values: 'super_admin', 'village_pdo', 'worker', 'citizen'.",
        )
