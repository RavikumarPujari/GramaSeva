from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.models.localities import LocalityUnit, Department, Organization
from app.auth.dependencies import require_roles

router = APIRouter(prefix="/localities", tags=["Localities & Village Wards"])

class LocalityUnitResponse(BaseModel):
    id: str
    organization_id: str
    unit_type: str
    parent_id: Optional[str] = None
    official_code: Optional[str] = None
    name_en: str
    name_kn: str
    name_hi: str
    is_active: bool

class CreateLocalityRequest(BaseModel):
    organization_id: str
    unit_type: str  # gram_panchayat, village, ward, etc.
    parent_id: Optional[str] = None
    official_code: Optional[str] = None
    name_en: str
    name_kn: str
    name_hi: str
    boundary_geojson: Optional[str] = None

class DepartmentResponse(BaseModel):
    id: str
    code: str
    name_en: str
    name_kn: str
    name_hi: str
    is_active: bool

@router.get("", response_model=List[LocalityUnitResponse])
def list_localities(
    unit_type: Optional[str] = None,
    parent_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(LocalityUnit).filter(LocalityUnit.is_active == True)
    if unit_type:
        query = query.filter(LocalityUnit.unit_type == unit_type)
    if parent_id:
        query = query.filter(LocalityUnit.parent_id == parent_id)
    return query.all()

@router.get("/{id}/children", response_model=List[LocalityUnitResponse])
def get_locality_children(id: str, db: Session = Depends(get_db)):
    parent = db.query(LocalityUnit).filter(LocalityUnit.id == id).first()
    if not parent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Locality unit not found",
        )
    return db.query(LocalityUnit).filter(LocalityUnit.parent_id == id, LocalityUnit.is_active == True).all()

@router.post("", response_model=LocalityUnitResponse, status_code=status.HTTP_201_CREATED)
def create_locality(
    req: CreateLocalityRequest,
    current_admin=Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """Admin-only endpoint to configure new villages, wards, or administrative units."""
    unit = LocalityUnit(
        organization_id=req.organization_id,
        unit_type=req.unit_type,
        parent_id=req.parent_id,
        official_code=req.official_code,
        name_en=req.name_en,
        name_kn=req.name_kn,
        name_hi=req.name_hi,
        boundary_geojson=req.boundary_geojson,
        is_active=True,
    )
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit

@router.get("/departments/list", response_model=List[DepartmentResponse])
def list_departments(db: Session = Depends(get_db)):
    return db.query(Department).filter(Department.is_active == True).all()
