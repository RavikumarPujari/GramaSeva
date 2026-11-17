from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
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

    role_assignments = relationship(
        "RoleAssignment",
        back_populates="profile",
        foreign_keys="[RoleAssignment.profile_id]",
        cascade="all, delete-orphan",
    )
    submissions = relationship("Submission", back_populates="reporter")

class RoleAssignment(Base, TimestampMixin):
    __tablename__ = "role_assignments"

    profile_id = Column(String(36), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    # Role: citizen, reviewer, worker, admin
    role = Column(String(50), nullable=False, index=True)
    # Optional department scoping (for field workers)
    department_id = Column(String(36), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    # Jurisdiction scoping: locality_unit_id this staff is authorized to manage
    jurisdiction_unit_id = Column(String(36), ForeignKey("locality_units.id", ondelete="SET NULL"), nullable=True, index=True)
    granted_by = Column(String(36), ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    valid_from = Column(DateTime, nullable=True)
    valid_to = Column(DateTime, nullable=True)

    profile = relationship("Profile", foreign_keys=[profile_id], back_populates="role_assignments")
    department = relationship("Department")
    jurisdiction_unit = relationship("LocalityUnit")
