import uuid
from typing import Any

from sqlalchemy import (
    CHAR,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    String,
    func,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from backend.core.db import Base

# Enums
PLAN_ENUM = ("free", "pro", "enterprise")
ROLE_ENUM = ("admin", "analyst", "viewer")
SCOPE_ENUM = ("1", "2", "3")
TRANSPORT_MODE_ENUM = ("air", "sea", "road", "rail")
REPORT_STATUS_ENUM = ("pending", "processing", "done", "failed")


class Organization(Base): # type: ignore
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    sector = Column(String(100))
    country = Column(CHAR(2))
    plan: Any = Column(SQLEnum(*PLAN_ENUM, name="plan_type"), default="free")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    suppliers = relationship("Supplier", back_populates="organization", cascade="all, delete-orphan")
    emission_records = relationship("EmissionRecord", back_populates="organization", cascade="all, delete-orphan")
    supply_chain_edges = relationship("SupplyChainEdge", back_populates="organization", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="organization", cascade="all, delete-orphan")
    ai_conversations = relationship("AIConversation", back_populates="organization", cascade="all, delete-orphan")


class User(Base): # type: ignore
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=True)  # bcrypt hash for local auth fallback
    role: Any = Column(SQLEnum(*ROLE_ENUM, name="role_type"), default="analyst")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    organization = relationship("Organization", back_populates="users")
    reports = relationship("Report", back_populates="user")
    ai_conversations = relationship("AIConversation", back_populates="user")


class Supplier(Base): # type: ignore
    __tablename__ = "suppliers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    country = Column(CHAR(2))
    sector = Column(String(100))
    emission_factor_kg_per_unit = Column(Float, default=1.0)
    esg_score = Column(Float)
    lat = Column(Float)
    lng = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("esg_score >= 0 AND esg_score <= 100", name="check_esg_score_range"),
    )

    # Relationships
    organization = relationship("Organization", back_populates="suppliers")
    emission_records = relationship("EmissionRecord", back_populates="supplier")


class EmissionRecord(Base): # type: ignore
    __tablename__ = "emission_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True)
    scope: Any = Column(SQLEnum(*SCOPE_ENUM, name="scope_type"), nullable=False)
    category = Column(String(100))
    amount_tco2e = Column(Float, nullable=False)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    source = Column(String(100), default="manual")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("amount_tco2e >= 0", name="check_amount_tco2e_positive"),
    )

    # Relationships
    organization = relationship("Organization", back_populates="emission_records")
    supplier = relationship("Supplier", back_populates="emission_records")


class SupplyChainEdge(Base): # type: ignore
    __tablename__ = "supply_chain_edges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    from_supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False)
    to_supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False)
    transport_mode: Any = Column(SQLEnum(*TRANSPORT_MODE_ENUM, name="transport_mode_type"), nullable=False)
    distance_km = Column(Float)
    weight_tonnes = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    organization = relationship("Organization", back_populates="supply_chain_edges")


class Report(Base): # type: ignore
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    generated_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    s3_url = Column(String)  # This will hold S3/storage url or locally served pdf path
    status: Any = Column(SQLEnum(*REPORT_STATUS_ENUM, name="report_status_type"), default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    organization = relationship("Organization", back_populates="reports")
    user = relationship("User", back_populates="reports")


class AIConversation(Base): # type: ignore
    __tablename__ = "ai_conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    messages = Column(JSONB, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    organization = relationship("Organization", back_populates="ai_conversations")
    user = relationship("User", back_populates="ai_conversations")
