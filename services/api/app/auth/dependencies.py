from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.config import settings
from app.auth.security import decode_access_token
from app.models.users import Profile, RoleAssignment
from app.models.localities import LocalityUnit

security_bearer = HTTPBearer(auto_error=False)

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: Session = Depends(get_db),
) -> Profile:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    payload = decode_access_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload["sub"]
    profile = db.query(Profile).filter(Profile.id == user_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found",
        )
    
    if not profile.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account has been deactivated",
        )
    
    return profile

def require_roles(*allowed_roles: str):
    """RBAC dependency: checks if user has at least one active assignment in allowed_roles."""
    def role_checker(
        current_user: Profile = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> Profile:
        user_roles = (
            db.query(RoleAssignment.role)
            .filter(RoleAssignment.profile_id == current_user.id, RoleAssignment.is_active == True)
            .all()
        )
        active_role_names = [r[0] for r in user_roles]

        # Admin has superuser access to all roles
        if "admin" in active_role_names:
            return current_user

        has_permission = any(role in active_role_names for role in allowed_roles)
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Requires one of roles: {list(allowed_roles)}. Your active roles: {active_role_names}",
            )
        return current_user

    return role_checker

def verify_jurisdiction_scope(
    db: Session,
    staff_profile_id: str,
    target_locality_unit_id: Optional[str],
) -> bool:
    """
    Checks if staff's assigned jurisdiction covers the target locality unit.
    Hierarchy: State -> District -> Taluk -> GP -> Village -> Ward.
    A staff member assigned to GP covers the GP, all its villages, and all wards within those villages.
    """
    if not target_locality_unit_id:
        return True  # If issue ward is unknown, root GP reviewers can triage it

    # Check staff role assignments with jurisdiction
    assignments = (
        db.query(RoleAssignment)
        .filter(
            RoleAssignment.profile_id == staff_profile_id,
            RoleAssignment.is_active == True,
        )
        .all()
    )

    # Admin bypass
    for a in assignments:
        if a.role == "admin" or not a.jurisdiction_unit_id:
            return True  # Global admin or unscoped staff

    # Walk up the parent hierarchy from target_locality_unit_id
    current_unit_id: Optional[str] = target_locality_unit_id
    scoped_jurisdiction_ids = {a.jurisdiction_unit_id for a in assignments if a.jurisdiction_unit_id}

    while current_unit_id:
        if current_unit_id in scoped_jurisdiction_ids:
            return True
        parent = db.query(LocalityUnit.parent_id).filter(LocalityUnit.id == current_unit_id).first()
        current_unit_id = parent[0] if parent else None

    return False

def verify_separation_of_duty(
    worker_id: Optional[str],
    reviewer_id: str,
) -> bool:
    """Enforces rule: A worker cannot approve their own repair resolution."""
    if worker_id and worker_id == reviewer_id:
        return False
    return True
