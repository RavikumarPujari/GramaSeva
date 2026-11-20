from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class TriageActionRequest(BaseModel):
    priority: str = Field(default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    department_id: str
    assigned_worker_id: Optional[str] = None
    corrected_category: Optional[str] = None
    corrected_ward_id: Optional[str] = None
    instructions: Optional[str] = None
    audit_reason: str = Field(default="Standard triage by authority reviewer")

class DuplicateDecisionRequest(BaseModel):
    submission_id: str
    target_issue_id: str
    decision: str  # LINK_DUPLICATE or KEEP_SEPARATE
    reason: str

class ResolutionReviewRequest(BaseModel):
    decision: str  # APPROVE, REQUEST_EVIDENCE, REOPEN, CORRECTION_REQUIRED, REJECT
    explanation: str
    verified_cost: Optional[float] = None
    cost_remarks: Optional[str] = None

class StaffInboxItem(BaseModel):
    submission_id: str
    tracking_id: str
    issue_id: str
    reference_number: str
    category: str
    description: Optional[str] = None
    status: str
    priority: str
    village_name: Optional[str] = None
    ward_name: Optional[str] = None
    locality_unit_id: Optional[str] = None
    submitted_at: datetime
    photos_count: int = 0

class ResolutionQueueItem(BaseModel):
    issue_id: str
    reference_number: str
    category: str
    village_name: Optional[str] = None
    ward_name: Optional[str] = None
    assigned_worker_name: Optional[str] = None
    assigned_worker_id: Optional[str] = None
    reported_repair_at: Optional[datetime] = None
    repair_notes: Optional[str] = None
    before_photo_ids: List[str] = []
    after_photo_ids: List[str] = []
    estimated_cost: Optional[float] = None
    proposed_cost: Optional[float] = None
    materials_cost: Optional[float] = None
    labour_cost: Optional[float] = None
    other_expenses_cost: Optional[float] = None
    verified_cost: Optional[float] = None
    cost_status: Optional[str] = None
    work_performed: Optional[str] = None
    materials_used: Optional[str] = None
    labour_details: Optional[str] = None

class DuplicateCandidateItem(BaseModel):
    issue_id: str
    reference_number: str
    category: str
    status: str
    distance_meters: float
    summary: Optional[str] = None
    village_name: Optional[str] = None
    ward_name: Optional[str] = None
    spatial_score: Optional[float] = None
    text_score: Optional[float] = None
    visual_score: Optional[float] = None
    composite_score: Optional[float] = None
    explanation: Optional[str] = None
    is_strong_candidate: Optional[bool] = None
    created_at: datetime
