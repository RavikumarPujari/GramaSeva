from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.issues import Asset, Issue
from app.models.users import Profile
from app.auth.dependencies import require_roles

router = APIRouter(prefix="/assets", tags=["Public Infrastructure Asset Register"])

class AssetResponse(BaseModel):
    id: str
    official_code: str
    name_en: str
    name_kn: Optional[str] = None
    name_hi: Optional[str] = None
    category: str
    locality_unit_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    condition_status: str
    active_issues_count: int = 0

class AssetDetailResponse(AssetResponse):
    linked_issue_ids: List[str] = []

class CreateAssetRequest(BaseModel):
    official_code: str
    name_en: str
    name_kn: Optional[str] = None
    name_hi: Optional[str] = None
    category: str  # road, water_point, street_light, drain
    locality_unit_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    condition_status: str = Field(default="OPERATIONAL")

@router.get("", response_model=List[AssetResponse])
def get_assets(
    category: Optional[str] = Query(None),
    locality_unit_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Returns verified municipal public infrastructure assets (README Section 5.2, Phase 8).
    Links issues to verified assets only when confirmed.
    """
    query = db.query(Asset)
    if category:
        query = query.filter(Asset.category == category)
    if locality_unit_id:
        query = query.filter(Asset.locality_unit_id == locality_unit_id)

    assets = query.all()
    out = []
    for a in assets:
        active_count = (
            db.query(Issue)
            .filter(Issue.asset_id == a.id, Issue.status.notin_(["RESOLVED", "REJECTED", "CANCELLED"]))
            .count()
        )
        out.append(
            AssetResponse(
                id=a.id,
                official_code=a.official_code,
                name_en=a.name_en,
                name_kn=a.name_kn,
                name_hi=a.name_hi,
                category=a.category,
                locality_unit_id=a.locality_unit_id,
                latitude=a.latitude,
                longitude=a.longitude,
                condition_status=a.condition_status,
                active_issues_count=active_count,
            )
        )
    return out

@router.get("/{id}", response_model=AssetDetailResponse)
def get_asset_detail(
    id: str,
    db: Session = Depends(get_db),
):
    """Returns detailed asset information and history of associated issues."""
    asset = db.query(Asset).filter((Asset.id == id) | (Asset.official_code == id)).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    linked_issues = db.query(Issue).filter(Issue.asset_id == asset.id).all()
    active_count = sum(1 for i in linked_issues if i.status not in ["RESOLVED", "REJECTED", "CANCELLED"])

    return AssetDetailResponse(
        id=asset.id,
        official_code=asset.official_code,
        name_en=asset.name_en,
        name_kn=asset.name_kn,
        name_hi=asset.name_hi,
        category=asset.category,
        locality_unit_id=asset.locality_unit_id,
        latitude=asset.latitude,
        longitude=asset.longitude,
        condition_status=asset.condition_status,
        active_issues_count=active_count,
        linked_issue_ids=[i.id for i in linked_issues],
    )

@router.post("", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
def create_asset(
    req: CreateAssetRequest,
    current_admin: Profile = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """Registers a verified municipal infrastructure asset (Admin only)."""
    existing = db.query(Asset).filter(Asset.official_code == req.official_code).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Asset code already exists")

    new_asset = Asset(
        official_code=req.official_code,
        name_en=req.name_en,
        name_kn=req.name_kn,
        name_hi=req.name_hi,
        category=req.category,
        locality_unit_id=req.locality_unit_id,
        latitude=req.latitude,
        longitude=req.longitude,
        condition_status=req.condition_status,
    )
    db.add(new_asset)
    db.commit()
    db.refresh(new_asset)

    return AssetResponse(
        id=new_asset.id,
        official_code=new_asset.official_code,
        name_en=new_asset.name_en,
        name_kn=new_asset.name_kn,
        name_hi=new_asset.name_hi,
        category=new_asset.category,
        locality_unit_id=new_asset.locality_unit_id,
        latitude=new_asset.latitude,
        longitude=new_asset.longitude,
        condition_status=new_asset.condition_status,
        active_issues_count=0,
    )
