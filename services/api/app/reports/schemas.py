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
    reporter_name: Optional[str] = None
    reporter_phone: Optional[str] = None
    is_guest: Optional[bool] = False
    location_method: Optional[str] = "GPS_VERIFIED"
    gps_accuracy: Optional[float] = None
    taluk_name: Optional[str] = "Belagavi Taluk"
    voice_transcription: Optional[str] = None
    annotated_media_id: Optional[str] = None
    ai_category_suggestion: Optional[str] = None
    ai_confidence: Optional[float] = None
    confirmed_latitude: Optional[float] = None
    confirmed_longitude: Optional[float] = None
    confirmed_village: Optional[str] = None
    confirmed_address: Optional[str] = None
    confirmation_method: Optional[str] = "CITIZEN_CONFIRMED"
    jurisdiction_status: Optional[str] = "VERIFIED"
    location_conflict_flag: Optional[bool] = False
    location_conflict_details: Optional[str] = None
    ocr_extracted_text: Optional[str] = None
    ocr_detections_json: Optional[str] = None
    landmark_candidates_json: Optional[str] = None
    photo_location_status: Optional[str] = None
    photo_location_provider: Optional[str] = None
    gps_timestamp: Optional[datetime] = None
    detected_village: Optional[str] = None
    detected_taluk: Optional[str] = None
    detected_district: Optional[str] = None
    detected_state: Optional[str] = None
    detected_country: Optional[str] = "India"
    detected_postal_code: Optional[str] = None
    google_place_id: Optional[str] = None
    geocoding_status: Optional[str] = None
    location_confirmation_status: Optional[str] = "UNCONFIRMED"

class DraftUpdateRequest(BaseModel):
    category: Optional[str] = None
    description: Optional[str] = None
    locale: Optional[str] = None
    village_name: Optional[str] = None
    ward_name: Optional[str] = None
    locality_unit_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    reporter_name: Optional[str] = None
    reporter_phone: Optional[str] = None
    is_guest: Optional[bool] = None
    location_method: Optional[str] = None
    gps_accuracy: Optional[float] = None
    taluk_name: Optional[str] = None
    voice_transcription: Optional[str] = None
    annotated_media_id: Optional[str] = None
    ai_category_suggestion: Optional[str] = None
    ai_confidence: Optional[float] = None
    confirmed_latitude: Optional[float] = None
    confirmed_longitude: Optional[float] = None
    confirmed_village: Optional[str] = None
    confirmed_address: Optional[str] = None
    confirmation_method: Optional[str] = None
    jurisdiction_status: Optional[str] = None
    location_conflict_flag: Optional[bool] = None
    location_conflict_details: Optional[str] = None
    ocr_extracted_text: Optional[str] = None
    ocr_detections_json: Optional[str] = None
    landmark_candidates_json: Optional[str] = None
    photo_location_status: Optional[str] = None
    photo_location_provider: Optional[str] = None
    gps_timestamp: Optional[datetime] = None
    detected_village: Optional[str] = None
    detected_taluk: Optional[str] = None
    detected_district: Optional[str] = None
    detected_state: Optional[str] = None
    detected_country: Optional[str] = "India"
    detected_postal_code: Optional[str] = None
    google_place_id: Optional[str] = None
    geocoding_status: Optional[str] = None
    location_confirmation_status: Optional[str] = "UNCONFIRMED"

class SubmitReportRequest(BaseModel):
    idempotency_key: Optional[str] = None
    is_anonymous: Optional[bool] = False
    duplicate_decision: Optional[str] = None  # CONFIRMED_DUPLICATE, REJECTED_DIFFERENT, UNCERTAIN_NEEDS_REVIEW
    duplicate_target_issue_id: Optional[str] = None
    reporter_name: Optional[str] = None
    reporter_phone: Optional[str] = None
    is_guest: Optional[bool] = None
    location_method: Optional[str] = None
    gps_accuracy: Optional[float] = None
    taluk_name: Optional[str] = None
    voice_transcription: Optional[str] = None
    annotated_media_id: Optional[str] = None
    ai_category_suggestion: Optional[str] = None
    ai_confidence: Optional[float] = None
    confirmed_latitude: Optional[float] = None
    confirmed_longitude: Optional[float] = None
    confirmed_village: Optional[str] = None
    confirmed_address: Optional[str] = None
    confirmation_method: Optional[str] = None
    jurisdiction_status: Optional[str] = None
    location_conflict_flag: Optional[bool] = None
    location_conflict_details: Optional[str] = None
    ocr_extracted_text: Optional[str] = None
    ocr_detections_json: Optional[str] = None
    landmark_candidates_json: Optional[str] = None
    photo_location_status: Optional[str] = None
    photo_location_provider: Optional[str] = None
    gps_timestamp: Optional[datetime] = None
    detected_village: Optional[str] = None
    detected_taluk: Optional[str] = None
    detected_district: Optional[str] = None
    detected_state: Optional[str] = None
    detected_country: Optional[str] = "India"
    detected_postal_code: Optional[str] = None
    google_place_id: Optional[str] = None
    geocoding_status: Optional[str] = None
    location_confirmation_status: Optional[str] = "UNCONFIRMED"

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

class DuplicateSuggestionItem(BaseModel):
    issue_id: str
    reference_number: str
    category: str
    status: str
    distance_meters: float
    summary: Optional[str] = None
    ward_name: Optional[str] = None
    composite_score: float
    explanation: str
    target_media_id: Optional[str] = None
    created_at: datetime

class CheckDuplicatesRequest(BaseModel):
    category: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    description: Optional[str] = None
    max_radius: Optional[float] = 1000.0

class ReportResponse(BaseModel):
    id: str
    issue_id: Optional[str] = None
    tracking_id: str
    category: str
    description: Optional[str] = None
    locale: str
    status: str
    village_name: Optional[str] = None
    ward_name: Optional[str] = None
    taluk_name: Optional[str] = "Belagavi Taluk"
    locality_unit_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    reporter_name: Optional[str] = None
    reporter_phone: Optional[str] = None
    is_guest: bool = False
    location_method: Optional[str] = "GPS_VERIFIED"
    gps_accuracy: Optional[float] = None
    voice_transcription: Optional[str] = None
    annotated_media_id: Optional[str] = None
    ai_category_suggestion: Optional[str] = None
    ai_confidence: Optional[float] = None
    confirmed_latitude: Optional[float] = None
    confirmed_longitude: Optional[float] = None
    confirmed_village: Optional[str] = None
    confirmed_address: Optional[str] = None
    confirmation_method: Optional[str] = "CITIZEN_CONFIRMED"
    jurisdiction_status: Optional[str] = "VERIFIED"
    location_conflict_flag: Optional[bool] = False
    location_conflict_details: Optional[str] = None
    ocr_extracted_text: Optional[str] = None
    ocr_detections_json: Optional[str] = None
    landmark_candidates_json: Optional[str] = None
    photo_location_status: Optional[str] = None
    photo_location_provider: Optional[str] = None
    gps_timestamp: Optional[datetime] = None
    detected_village: Optional[str] = None
    detected_taluk: Optional[str] = None
    detected_district: Optional[str] = None
    detected_state: Optional[str] = None
    detected_country: Optional[str] = "India"
    detected_postal_code: Optional[str] = None
    google_place_id: Optional[str] = None
    geocoding_status: Optional[str] = None
    location_confirmation_status: Optional[str] = "UNCONFIRMED"
    clarification_message: Optional[str] = None
    clarification_response: Optional[str] = None
    rejection_reason: Optional[str] = None
    rejection_by_id: Optional[str] = None
    is_demo: Optional[bool] = False
    verified_cost: Optional[float] = None
    cost_status: Optional[str] = None
    work_completed_at: Optional[datetime] = None
    created_at: datetime
    media_assets: List[MediaAssetResponse] = []
    timeline: List[StatusEventResponse] = []

class OfflineDraftSyncItem(BaseModel):
    client_draft_id: str
    idempotency_key: str
    category: str = Field(default="road_damage")
    description: Optional[str] = None
    locale: Optional[str] = "en"
    village_name: Optional[str] = None
    ward_name: Optional[str] = None
    locality_unit_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class SyncReportResponse(BaseModel):
    synced_count: int
    items: List[ReportResponse]
