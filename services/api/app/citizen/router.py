import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.users import Profile, CitizenWardRegistration, CitizenDocument
from app.models.localities import LocalityUnit
from app.models.issues import Notification
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/citizen", tags=["Citizen Civic Portal & Profile"])

# --- Schemas ---

class UpdateCitizenProfileRequest(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    address: Optional[str] = None
    taluk: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    avatar_url: Optional[str] = None

class RegisterWardRequest(BaseModel):
    ward_unit_id: str
    is_primary: bool = False
    residence_type: str = "RESIDENT"  # RESIDENT, PROPERTY_OWNER, COMMUTER, OTHER

class AddDocumentRequest(BaseModel):
    title: str
    document_type: str  # RATION_CARD, AADHAAR_MASKED, PROPERTY_TAX_RECEIPT, ELECTRICITY_BILL, OTHER
    file_url: str
    file_size_bytes: int = 0

# --- Endpoints ---

@router.get("/profile")
def get_citizen_profile(
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get the authenticated citizen's personal profile and registered wards.
    Protected strictly by auth; citizens can only see their own profile.
    """
    wards = (
        db.query(CitizenWardRegistration)
        .filter(CitizenWardRegistration.profile_id == current_user.id)
        .all()
    )

    ward_list = []
    for reg in wards:
        unit = db.query(LocalityUnit).filter(LocalityUnit.id == reg.ward_unit_id).first()
        village_name = None
        if unit and unit.parent_id:
            parent = db.query(LocalityUnit.name_en).filter(LocalityUnit.id == unit.parent_id).first()
            village_name = parent[0] if parent else None

        ward_list.append({
            "registration_id": reg.id,
            "ward_id": reg.ward_unit_id,
            "ward_name": unit.name_en if unit else "Unknown Ward",
            "village_name": village_name,
            "is_primary": reg.is_primary,
            "residence_type": reg.residence_type,
            "verification_status": reg.verification_status,
        })

    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "phone_number": current_user.phone_number,
        "preferred_locale": current_user.preferred_locale,
        "address": current_user.address or "Gowdanahalli Village",
        "taluk": current_user.taluk or "Pandavapura",
        "district": current_user.district or "Mandya",
        "state": current_user.state or "Karnataka",
        "avatar_url": current_user.avatar_url,
        "registered_wards": ward_list,
        "verification_status": "VERIFIED_RESIDENT",
    }

@router.patch("/profile")
def update_citizen_profile(
    req: UpdateCitizenProfileRequest,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update citizen editable profile information.
    """
    profile = db.query(Profile).filter(Profile.id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    if req.full_name is not None:
        profile.full_name = req.full_name.strip()
    if req.phone_number is not None:
        profile.phone_number = req.phone_number.strip()
    if req.address is not None:
        profile.address = req.address.strip()
    if req.taluk is not None:
        profile.taluk = req.taluk.strip()
    if req.district is not None:
        profile.district = req.district.strip()
    if req.state is not None:
        profile.state = req.state.strip()
    if req.avatar_url is not None:
        profile.avatar_url = req.avatar_url.strip()

    db.commit()
    db.refresh(profile)

    return {
        "status": "success",
        "full_name": profile.full_name,
        "phone_number": profile.phone_number,
        "address": profile.address,
        "taluk": profile.taluk,
        "district": profile.district,
        "state": profile.state,
    }

@router.get("/wards")
def get_citizen_wards(
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all wards associated with this citizen.
    """
    wards = (
        db.query(CitizenWardRegistration)
        .filter(CitizenWardRegistration.profile_id == current_user.id)
        .all()
    )

    results = []
    for reg in wards:
        unit = db.query(LocalityUnit).filter(LocalityUnit.id == reg.ward_unit_id).first()
        village_name = None
        if unit and unit.parent_id:
            parent = db.query(LocalityUnit.name_en).filter(LocalityUnit.id == unit.parent_id).first()
            village_name = parent[0] if parent else None

        results.append({
            "registration_id": reg.id,
            "ward_id": reg.ward_unit_id,
            "ward_name": unit.name_en if unit else "Ward",
            "village_name": village_name,
            "is_primary": reg.is_primary,
            "residence_type": reg.residence_type,
            "verification_status": reg.verification_status,
            "created_at": reg.created_at.isoformat() if reg.created_at else None,
        })
    return results

@router.post("/wards")
def register_citizen_ward(
    req: RegisterWardRequest,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Associate an additional ward with this citizen.
    Supports multiple wards (home, workplace, family ward).
    """
    ward = db.query(LocalityUnit).filter(LocalityUnit.id == req.ward_unit_id).first()
    if not ward:
        raise HTTPException(status_code=404, detail="Ward not found")

    # If is_primary requested, unset previous primary
    if req.is_primary:
        db.query(CitizenWardRegistration).filter(
            CitizenWardRegistration.profile_id == current_user.id
        ).update({"is_primary": False})

    reg = CitizenWardRegistration(
        id=str(uuid.uuid4()),
        profile_id=current_user.id,
        ward_unit_id=req.ward_unit_id,
        is_primary=req.is_primary,
        residence_type=req.residence_type,
        verification_status="SELF_DECLARED",
    )
    db.add(reg)
    db.commit()
    db.refresh(reg)

    return {
        "status": "success",
        "registration_id": reg.id,
        "ward_id": reg.ward_unit_id,
        "ward_name": ward.name_en,
        "is_primary": reg.is_primary,
        "verification_status": reg.verification_status,
    }

@router.delete("/wards/{registration_id}")
def delete_citizen_ward(
    registration_id: str,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Remove an associated ward.
    """
    reg = (
        db.query(CitizenWardRegistration)
        .filter(
            CitizenWardRegistration.id == registration_id,
            CitizenWardRegistration.profile_id == current_user.id,
        )
        .first()
    )
    if not reg:
        raise HTTPException(status_code=404, detail="Ward registration not found")

    db.delete(reg)
    db.commit()
    return {"status": "success", "message": "Ward association removed"}

@router.get("/documents")
def get_citizen_documents(
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Secure list of citizen's uploaded documents.
    """
    docs = (
        db.query(CitizenDocument)
        .filter(CitizenDocument.profile_id == current_user.id)
        .order_by(CitizenDocument.created_at.desc())
        .all()
    )

    return [
        {
            "id": d.id,
            "title": d.title,
            "document_type": d.document_type,
            "file_url": d.file_url,
            "file_size_bytes": d.file_size_bytes,
            "verification_status": d.verification_status,
            "rejection_reason": d.rejection_reason,
            "uploaded_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in docs
    ]

@router.post("/documents")
def add_citizen_document(
    req: AddDocumentRequest,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Register a newly uploaded document.
    """
    doc = CitizenDocument(
        id=str(uuid.uuid4()),
        profile_id=current_user.id,
        title=req.title.strip(),
        document_type=req.document_type,
        file_url=req.file_url.strip(),
        file_size_bytes=req.file_size_bytes,
        verification_status="PENDING",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return {
        "status": "success",
        "id": doc.id,
        "title": doc.title,
        "document_type": doc.document_type,
        "verification_status": doc.verification_status,
    }

@router.delete("/documents/{doc_id}")
def delete_citizen_document(
    doc_id: str,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a citizen document.
    """
    doc = (
        db.query(CitizenDocument)
        .filter(CitizenDocument.id == doc_id, CitizenDocument.profile_id == current_user.id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    db.delete(doc)
    db.commit()
    return {"status": "success", "message": "Document deleted"}

@router.get("/notifications")
def get_citizen_notifications(
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Live notifications for the citizen on complaint status changes.
    """
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
