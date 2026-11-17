from sqlalchemy import Column, String, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin

class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"

    name = Column(String(255), nullable=False)
    code = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    locality_units = relationship("LocalityUnit", back_populates="organization")
    departments = relationship("Department", back_populates="organization")

class LocalityUnit(Base, TimestampMixin):
    __tablename__ = "locality_units"

    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    # Unit type: state, district, taluk, block, gram_panchayat, village, ward, zone, urban_local_body, hamlet
    unit_type = Column(String(50), nullable=False, index=True)
    parent_id = Column(String(36), ForeignKey("locality_units.id", ondelete="CASCADE"), nullable=True, index=True)
    official_code = Column(String(50), nullable=True, index=True)
    
    # Multilingual display names (English, Kannada, Hindi)
    name_en = Column(String(255), nullable=False)
    name_kn = Column(String(255), nullable=False)
    name_hi = Column(String(255), nullable=False)

    # Spatial boundaries in GeoJSON (supports PostGIS geometry in PostgreSQL)
    boundary_geojson = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    organization = relationship("Organization", back_populates="locality_units")
    parent = relationship("LocalityUnit", remote_side="LocalityUnit.id", backref="children")
    issues = relationship("Issue", back_populates="locality_unit")

class Department(Base, TimestampMixin):
    __tablename__ = "departments"

    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    code = Column(String(50), nullable=False, index=True)
    name_en = Column(String(255), nullable=False)
    name_kn = Column(String(255), nullable=False)
    name_hi = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    organization = relationship("Organization", back_populates="departments")
    department_jurisdictions = relationship("DepartmentJurisdiction", back_populates="department")

class DepartmentJurisdiction(Base, TimestampMixin):
    __tablename__ = "department_jurisdictions"

    department_id = Column(String(36), ForeignKey("departments.id", ondelete="CASCADE"), nullable=False, index=True)
    locality_unit_id = Column(String(36), ForeignKey("locality_units.id", ondelete="CASCADE"), nullable=False, index=True)

    department = relationship("Department", back_populates="department_jurisdictions")
    locality_unit = relationship("LocalityUnit")
