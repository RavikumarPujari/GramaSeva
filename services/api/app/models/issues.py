from sqlalchemy import Column, String, Boolean, ForeignKey, Integer, Float, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base
from app.models.base import TimestampMixin

class Issue(Base, TimestampMixin):
    """The shared physical issue record. Multiple citizen submissions may link to one issue."""
    __tablename__ = "issues"

    reference_number = Column(String(50), unique=True, index=True, nullable=False)
    category = Column(String(50), index=True, nullable=False)
    # Lifecycle status
    status = Column(String(50), default="SUBMITTED", index=True, nullable=False)
    priority = Column(String(20), default="MEDIUM", index=True, nullable=False)
    
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    # Locality unit (ward where known, or village)
    locality_unit_id = Column(String(36), ForeignKey("locality_units.id", ondelete="SET NULL"), nullable=True, index=True)

    # Operational coordinates (restricted to authorized staff)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Generalized public coordinates (for privacy on public maps)
    public_latitude = Column(Float, nullable=True)
    public_longitude = Column(Float, nullable=True)

    # Department and worker assignment
    department_id = Column(String(36), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    assigned_worker_id = Column(String(36), ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True)
    
    # Independent review fields
    reviewed_by_id = Column(String(36), ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolution_review_notes = Column(Text, nullable=True)

    locality_unit = relationship("LocalityUnit", back_populates="issues")
    department = relationship("Department")
    assigned_worker = relationship("Profile", foreign_keys=[assigned_worker_id])
    reviewed_by = relationship("Profile", foreign_keys=[reviewed_by_id])
    submissions = relationship("Submission", back_populates="issue")
    media_assets = relationship("MediaAsset", back_populates="issue")
    assignments = relationship("Assignment", back_populates="issue")
    repair_reviews = relationship("RepairReview", back_populates="issue")
    status_events = relationship("StatusEvent", back_populates="issue")

class Submission(Base, TimestampMixin):
    """An individual citizen's complaint report. Preserved permanently even when linked to an issue."""
    __tablename__ = "submissions"

    tracking_id = Column(String(50), unique=True, index=True, nullable=False)
    reporter_id = Column(String(36), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    issue_id = Column(String(36), ForeignKey("issues.id", ondelete="SET NULL"), nullable=True, index=True)

    category = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    locale = Column(String(10), default="en", nullable=False)
    original_text = Column(Text, nullable=True)

    # Locality context entered by citizen
    locality_unit_id = Column(String(36), ForeignKey("locality_units.id", ondelete="SET NULL"), nullable=True)
    village_name = Column(String(255), nullable=True)
    ward_name = Column(String(255), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    is_anonymous = Column(Boolean, default=False, nullable=False)

    reporter = relationship("Profile", back_populates="submissions")
    issue = relationship("Issue", back_populates="submissions")
    media_assets = relationship("MediaAsset", back_populates="submission")

class MediaAsset(Base, TimestampMixin):
    __tablename__ = "media_assets"

    profile_id = Column(String(36), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)
    submission_id = Column(String(36), ForeignKey("submissions.id", ondelete="CASCADE"), nullable=True, index=True)
    issue_id = Column(String(36), ForeignKey("issues.id", ondelete="CASCADE"), nullable=True, index=True)

    # Role: CITIZEN_BEFORE, WORKER_PROGRESS, WORKER_AFTER
    evidence_role = Column(String(50), nullable=False)
    storage_path = Column(String(500), nullable=False)
    file_hash = Column(String(64), nullable=True)  # SHA-256
    mime_type = Column(String(100), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)

    is_quarantined = Column(Boolean, default=True, nullable=False)
    is_public_approved = Column(Boolean, default=False, nullable=False)

    submission = relationship("Submission", back_populates="media_assets")
    issue = relationship("Issue", back_populates="media_assets")

class DuplicateCandidate(Base, TimestampMixin):
    __tablename__ = "duplicate_candidates"

    submission_id = Column(String(36), ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False, index=True)
    target_issue_id = Column(String(36), ForeignKey("issues.id", ondelete="CASCADE"), nullable=False, index=True)
    
    detection_method = Column(String(50), nullable=False)  # spatial_proximity, category_match, visual_similarity
    distance_meters = Column(Float, nullable=True)
    similarity_score = Column(Float, nullable=True)
    
    # Decision: PENDING, CONFIRMED_DUPLICATE, REJECTED_DIFFERENT
    decision = Column(String(50), default="PENDING", index=True, nullable=False)
    adjudicated_by_id = Column(String(36), ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True)
    adjudicated_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

class Assignment(Base, TimestampMixin):
    __tablename__ = "assignments"

    issue_id = Column(String(36), ForeignKey("issues.id", ondelete="CASCADE"), nullable=False, index=True)
    department_id = Column(String(36), ForeignKey("departments.id", ondelete="CASCADE"), nullable=False)
    worker_profile_id = Column(String(36), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_by_id = Column(String(36), ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True)
    
    # Status: ASSIGNED, ACCEPTED, DECLINED, IN_PROGRESS, COMPLETED
    status = Column(String(50), default="ASSIGNED", nullable=False)
    instructions = Column(Text, nullable=True)
    decline_reason = Column(Text, nullable=True)

    issue = relationship("Issue", back_populates="assignments")
    worker = relationship("Profile", foreign_keys=[worker_profile_id])
    assigned_by = relationship("Profile", foreign_keys=[assigned_by_id])

class RepairReview(Base, TimestampMixin):
    __tablename__ = "repair_reviews"

    issue_id = Column(String(36), ForeignKey("issues.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_profile_id = Column(String(36), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Decision: APPROVED, EVIDENCE_REQUESTED, REOPENED
    decision = Column(String(50), nullable=False)
    explanation = Column(Text, nullable=False)
    reviewed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    issue = relationship("Issue", back_populates="repair_reviews")

class Dispute(Base, TimestampMixin):
    __tablename__ = "disputes"

    issue_id = Column(String(36), ForeignKey("issues.id", ondelete="CASCADE"), nullable=False, index=True)
    citizen_profile_id = Column(String(36), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    reason = Column(Text, nullable=False)
    status = Column(String(50), default="OPEN", nullable=False)  # OPEN, RESOLVED_UPHELD, REOPENED
    response_notes = Column(Text, nullable=True)
    resolved_by_id = Column(String(36), ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True)

class Feedback(Base, TimestampMixin):
    """Citizen rating and feedback for verified resolved issues."""
    __tablename__ = "feedback"

    issue_id = Column(String(36), ForeignKey("issues.id", ondelete="CASCADE"), nullable=False, index=True)
    citizen_profile_id = Column(String(36), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    rating = Column(Integer, nullable=False)  # 1 to 5
    comment = Column(Text, nullable=True)
    is_satisfied = Column(Boolean, default=True, nullable=False)

    issue = relationship("Issue")
    citizen = relationship("Profile")

class Notification(Base, TimestampMixin):
    """In-app notifications with idempotent deduplication keys."""
    __tablename__ = "notifications"

    profile_id = Column(String(36), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    issue_id = Column(String(36), ForeignKey("issues.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    locale = Column(String(10), default="en", nullable=False)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    dedup_key = Column(String(150), unique=True, index=True, nullable=False)

    profile = relationship("Profile")
    issue = relationship("Issue")

class StatusEvent(Base, TimestampMixin):
    """Immutable audit trail for every issue state transition."""
    __tablename__ = "status_events"

    issue_id = Column(String(36), ForeignKey("issues.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_profile_id = Column(String(36), ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True)
    previous_status = Column(String(50), nullable=True)
    next_status = Column(String(50), nullable=False)
    reason = Column(Text, nullable=True)

    issue = relationship("Issue", back_populates="status_events")

class AuditLog(Base, TimestampMixin):
    """Immutable record of privileged operations (RBAC grant, jurisdiction change, deletion)."""
    __tablename__ = "audit_logs"

    actor_profile_id = Column(String(36), ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)
    target_type = Column(String(100), nullable=False)
    target_id = Column(String(36), nullable=False)
    details_json = Column(Text, nullable=True)
    client_ip = Column(String(50), nullable=True)

class Job(Base, TimestampMixin):
    """Persistent background tasks queue (AI inference, notifications, exports)."""
    __tablename__ = "jobs"

    task_name = Column(String(100), nullable=False, index=True)
    payload_json = Column(Text, nullable=False)
    # Status: QUEUED, PROCESSING, COMPLETED, FAILED
    status = Column(String(50), default="QUEUED", index=True, nullable=False)
    retry_count = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

class ModelRun(Base, TimestampMixin):
    """Immutable record of real AI inference runs, metrics, detections, and human confirmations."""
    __tablename__ = "model_runs"

    job_id = Column(String(36), nullable=True, index=True)
    media_asset_id = Column(String(36), ForeignKey("media_assets.id", ondelete="CASCADE"), nullable=True, index=True)
    issue_id = Column(String(36), ForeignKey("issues.id", ondelete="CASCADE"), nullable=True, index=True)
    submission_id = Column(String(36), ForeignKey("submissions.id", ondelete="CASCADE"), nullable=True, index=True)

    model_id = Column(String(100), nullable=False, index=True)
    model_revision = Column(String(64), nullable=False)
    task = Column(String(50), nullable=False)
    # Status: COMPLETED, FAILED, UNAVAILABLE, NO_DETECTIONS
    status = Column(String(50), default="COMPLETED", nullable=False)
    category_suggestion = Column(String(50), nullable=True)
    confidence_score = Column(Float, nullable=True)
    detections_json = Column(Text, nullable=True)
    latency_ms = Column(Integer, default=0, nullable=False)
    requires_human_review = Column(Boolean, default=True, nullable=False)
    limitations_json = Column(Text, nullable=True)

    # Human review / confirmation
    confirmed_by_profile_id = Column(String(36), ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True)
    confirmed_decision = Column(String(50), default="PENDING", nullable=False)  # PENDING, CONFIRMED, REJECTED

    media_asset = relationship("MediaAsset")
    issue = relationship("Issue")
    submission = relationship("Submission")
    confirmed_by = relationship("Profile")
