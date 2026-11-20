from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
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
    profile = db.query(Profile).filter(Profile.email == req.email.lower()).first()
    if not profile or not verify_password(req.password, profile.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
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

    active_role_names = [a.role for a in assignments]

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
        
        # Check permission: Admin has bypass for administrative review
        has_role = (expected_role in active_role_names) or ("admin" in active_role_names and expected_role in ["admin", "reviewer"])
        if not has_role:
            role_display_names = {
                "admin": "Super Admin",
                "reviewer": "Village PDO",
                "worker": "Worker",
                "citizen": "Citizen",
            }
            display_expected = role_display_names.get(expected_role, expected_role)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: This account is not registered as a {display_expected}. Please select your authorized role.",
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
        "roles": roles_data,
        "is_approved": is_approved,
        "approval_status": overall_approval_status,
    }
