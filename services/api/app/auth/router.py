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

class LoginRequest(BaseModel):
    email: str
    password: str

class RoleInfo(BaseModel):
    role: str
    jurisdiction_unit_id: Optional[str] = None
    jurisdiction_name: Optional[str] = None
    department_id: Optional[str] = None

class ProfileResponse(BaseModel):
    id: str
    email: str
    full_name: str
    preferred_locale: str
    roles: List[RoleInfo]

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
            "roles": [{"role": "citizen"}],
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
            detail="Account is deactivated",
        )

    roles_data: List[RoleInfo] = []
    assignments = (
        db.query(RoleAssignment)
        .filter(RoleAssignment.profile_id == profile.id, RoleAssignment.is_active == True)
        .all()
    )
    for a in assignments:
        jur_name = None
        if a.jurisdiction_unit_id:
            unit = db.query(LocalityUnit).filter(LocalityUnit.id == a.jurisdiction_unit_id).first()
            if unit:
                jur_name = unit.name_en
        roles_data.append(
            RoleInfo(
                role=a.role,
                jurisdiction_unit_id=a.jurisdiction_unit_id,
                jurisdiction_name=jur_name,
                department_id=a.department_id,
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
    for a in assignments:
        jur_name = None
        if a.jurisdiction_unit_id:
            unit = db.query(LocalityUnit).filter(LocalityUnit.id == a.jurisdiction_unit_id).first()
            if unit:
                jur_name = unit.name_en
        roles_data.append(
            RoleInfo(
                role=a.role,
                jurisdiction_unit_id=a.jurisdiction_unit_id,
                jurisdiction_name=jur_name,
                department_id=a.department_id,
            )
        )

    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "preferred_locale": current_user.preferred_locale,
        "roles": roles_data,
    }
