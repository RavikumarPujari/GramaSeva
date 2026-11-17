from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class DraftCreateRequest(BaseModel):
    category: str = Field(default="road_damage")
    description: Optional[str] = None
    locale: Optional[str] = "en"
    village_name: Optional[str] = None
    ward_name: Optional[str] = None
    locality_unit_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    idempotency_key: Optional[str] = None

class DraftUpdateRequest(BaseModel):
    category: Optional[str] = None
    description: Optional[str] = None
    locale: Optional[str] = None
    village_name: Optional[str] = None
    ward_name: Optional[str] = None
    locality_unit_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class SubmitReportRequest(BaseModel):
    idempotency_key: Optional[str] = None
    is_anonymous: Optional[bool] = False

class MediaAssetResponse(BaseModel):
    id: str
    evidence_role: str
    mime_type: str
    file_size_bytes: int
    file_hash: Optional[str] = None
    is_quarantined: bool

class StatusEventResponse(BaseModel):
    previous_status: Optional[str] = None
    next_status: str
    reason: Optional[str] = None
    created_at: datetime

class ReportResponse(BaseModel):
    id: str
    tracking_id: str
    category: str
    description: Optional[str] = None
    locale: str
    status: str
    village_name: Optional[str] = None
    ward_name: Optional[str] = None
    locality_unit_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_at: datetime
    media_assets: List[MediaAssetResponse] = []
    timeline: List[StatusEventResponse] = []
