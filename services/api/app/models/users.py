from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime, Text, Integer
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base
from app.models.base import TimestampMixin

class Profile(Base, TimestampMixin):
    __tablename__ = "profiles"

    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    phone_number = Column(String(50), nullable=True)  # Strictly private
    preferred_locale = Column(String(10), default="en", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Citizen profile extended attributes
    address = Column(Text, nullable=True)
    taluk = Column(String(100), default="Pandavapura", nullable=True)
    district = Column(String(100), default="Mandya", nullable=True)
    state = Column(String(100), default="Karnataka", nullable=True)
    avatar_url = Column(String(500), nullable=True)

    role_assignments = relationship(
        "RoleAssignment",
        back_populates="profile",
        foreign_keys="[RoleAssignment.profile_id]",
        cascade="all, delete-orphan",
    )
    submissions = relationship("Submission", back_populates="reporter")
    ward_registrations = relationship(
        "CitizenWardRegistration",
        back_populates="profile",
        cascade="all, delete-orphan",
    )
    documents = relationship(
        "CitizenDocument",
        back_populates="profile",
        cascade="all, delete-orphan",
    )

class RoleAssignment(Base, TimestampMixin):
    __tablename__ = "role_assignments"

    profile_id = Column(String(36), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    # Role: citizen, reviewer, worker, admin (reviewer = Village PDO)
    role = Column(String(50), nullable=False, index=True)
    # Optional department scoping (for field workers)
    department_id = Column(String(36), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    # Jurisdiction scoping: locality_unit_id this staff is authorized to manage (Gram Panchayat / Village)
    jurisdiction_unit_id = Column(String(36), ForeignKey("locality_units.id", ondelete="SET NULL"), nullable=True, index=True)
    granted_by = Column(String(36), ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    # Worker approval workflow: PENDING, APPROVED, REJECTED, SUSPENDED
    approval_status = Column(String(50), default="APPROVED", nullable=False)
    # Exactly one primary PDO assigned per Gram Panchayat
    is_primary = Column(Boolean, default=False, nullable=False)
    valid_from = Column(DateTime, nullable=True)
    valid_to = Column(DateTime, nullable=True)

    profile = relationship("Profile", foreign_keys=[profile_id], back_populates="role_assignments")
    department = relationship("Department")
    jurisdiction_unit = relationship("LocalityUnit")

class CitizenWardRegistration(Base, TimestampMixin):
    """Citizen multiple ward registrations."""
    __tablename__ = "citizen_ward_registrations"

    profile_id = Column(String(36), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    ward_unit_id = Column(String(36), ForeignKey("locality_units.id", ondelete="CASCADE"), nullable=False, index=True)
    is_primary = Column(Boolean, default=False, nullable=False)
    residence_type = Column(String(50), default="RESIDENT", nullable=False)  # RESIDENT, PROPERTY_OWNER, COMMUTER
    verification_status = Column(String(50), default="SELF_DECLARED", nullable=False)  # VERIFIED, PENDING_VERIFICATION, SELF_DECLARED

    profile = relationship("Profile", back_populates="ward_registrations")
    ward = relationship("LocalityUnit")

class CitizenDocument(Base, TimestampMixin):
    """Citizen uploaded verification documents."""
    __tablename__ = "citizen_documents"

    profile_id = Column(String(36), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    document_type = Column(String(50), nullable=False)  # RATION_CARD, AADHAAR_MASKED, PROPERTY_TAX_RECEIPT, ELECTRICITY_BILL, OTHER
    file_url = Column(String(500), nullable=False)
    file_size_bytes = Column(Integer, default=0, nullable=False)
    verification_status = Column(String(50), default="PENDING", nullable=False)  # VERIFIED, PENDING, REJECTED
    rejection_reason = Column(Text, nullable=True)

    profile = relationship("Profile", back_populates="documents")

class WardMember(Base, TimestampMixin):
    """Elected or appointed Ward Member registered in a village ward."""
    __tablename__ = "ward_members"

    ward_unit_id = Column(String(36), ForeignKey("locality_units.id", ondelete="CASCADE"), nullable=False, index=True)
    profile_id = Column(String(36), ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True)
    full_name = Column(String(255), nullable=False)
    phone_number = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    designation = Column(String(100), default="Ward Member", nullable=False)
    term_start = Column(DateTime, nullable=True)
    term_end = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    ward = relationship("LocalityUnit")
    profile = relationship("Profile")

class Announcement(Base, TimestampMixin):
    """Super Admin Taluk-level announcement broadcast."""
    __tablename__ = "announcements"

    sender_id = Column(String(36), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    target_type = Column(String(50), nullable=False)  # ALL_PDOS, SELECTED_VILLAGES, INDIVIDUAL_PDO
    target_village_ids = Column(Text, nullable=True)   # JSON or comma-separated list of locality_unit_ids
    target_pdo_id = Column(String(36), ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True)
    delivered_count = Column(Integer, default=0, nullable=False)

    sender = relationship("Profile", foreign_keys=[sender_id])
    target_pdo = relationship("Profile", foreign_keys=[target_pdo_id])
