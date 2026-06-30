from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator


# Base Config
class BaseSchema(BaseModel):
    model_config = {"from_attributes": True}


# Organization Schemas
class OrganizationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    sector: str | None = Field(None, max_length=100)
    country: str | None = Field(None, max_length=2)
    plan: str | None = "free"


class OrganizationCreate(OrganizationBase):
    pass


class Organization(BaseSchema, OrganizationBase):
    id: UUID
    created_at: datetime
    baseline_year: int | None = None
    target_reduction_pct: float = 20.0
    net_zero_target_year: int | None = None


# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    role: str | None = "analyst"


class UserCreate(UserBase):
    org_id: UUID
    password: str | None = None


class User(BaseSchema, UserBase):
    id: UUID
    org_id: UUID
    created_at: datetime


# Supplier Schemas
class SupplierBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    country: str | None = Field(None, max_length=2)
    sector: str | None = Field(None, max_length=100)
    emission_factor_kg_per_unit: float | None = Field(1.0, ge=0, le=1000)
    esg_score: float | None = Field(None, ge=0, le=100)
    lat: float | None = Field(None, ge=-90, le=90)
    lng: float | None = Field(None, ge=-180, le=180)


class SupplierCreate(SupplierBase):
    pass


class Supplier(BaseSchema, SupplierBase):
    id: UUID
    org_id: UUID
    created_at: datetime


# Emission Record Schemas
class EmissionRecordBase(BaseModel):
    supplier_id: UUID | None = None
    scope: str = Field(..., pattern="^[123]$")
    category: str | None = Field(None, max_length=100)
    amount_tco2e: float = Field(..., ge=0, le=1_000_000)
    period_start: date
    period_end: date
    source: str | None = Field("manual", max_length=100)

    @model_validator(mode="after")
    def validate_period(self) -> "EmissionRecordBase":
        if self.period_start > self.period_end:
            raise ValueError("period_start must be <= period_end")
        return self


class EmissionRecordCreate(EmissionRecordBase):
    pass


class EmissionRecord(BaseSchema, EmissionRecordBase):
    id: UUID
    org_id: UUID
    created_at: datetime


# Supply Chain Edge Schemas
class SupplyChainEdgeBase(BaseModel):
    from_supplier_id: UUID
    to_supplier_id: UUID
    transport_mode: str = Field(..., pattern="^(air|sea|road|rail)$")
    distance_km: float | None = Field(None, ge=0, le=50_000)
    weight_tonnes: float | None = Field(None, ge=0, le=1_000_000)

    @model_validator(mode="after")
    def validate_no_self_loop(self) -> "SupplyChainEdgeBase":
        if self.from_supplier_id == self.to_supplier_id:
            raise ValueError("from_supplier_id and to_supplier_id cannot be the same (self-loop)")
        return self


class SupplyChainEdgeCreate(SupplyChainEdgeBase):
    pass


class SupplyChainEdge(BaseSchema, SupplyChainEdgeBase):
    id: UUID
    org_id: UUID
    created_at: datetime


# Report Schemas
class ReportBase(BaseModel):
    period_start: date
    period_end: date

    @model_validator(mode="after")
    def validate_period(self) -> "ReportBase":
        if self.period_start > self.period_end:
            raise ValueError("period_start must be <= period_end")
        return self


class ReportCreate(ReportBase):
    pass


class Report(BaseSchema, ReportBase):
    id: UUID
    org_id: UUID
    generated_by: UUID | None = None
    s3_url: str | None = None
    status: str
    report_type: str = "sustainability"
    created_at: datetime


# AI Conversation Schemas
class MessageSchema(BaseModel):
    role: str = Field(..., max_length=20)
    content: str = Field(..., max_length=10_000)
    timestamp: str | None = None


class AIConversationBase(BaseModel):
    messages: list[MessageSchema] = []


class AIConversationCreate(AIConversationBase):
    pass


class AIConversation(BaseSchema, AIConversationBase):
    id: UUID
    org_id: UUID
    user_id: UUID
    created_at: datetime


# Auth response
class Token(BaseModel):
    access_token: str
    token_type: str
    user: User


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    org_name: str = Field(..., min_length=1, max_length=255)
    sector: str | None = Field(None, max_length=100)
    country: str | None = Field(None, max_length=2)


# ─── Compliance / Alert Schemas ────────────────────────────────────────────────

class Recommendation(BaseModel):
    title: str
    description: str
    category: str
    estimated_impact_pct: float | None = None


class ComplianceThresholdBase(BaseModel):
    scope: str = Field(..., pattern="^(1|2|3|total)$")
    threshold_tco2e: float = Field(..., gt=0)


class ComplianceThresholdCreate(ComplianceThresholdBase):
    pass


class ComplianceThreshold(BaseSchema, ComplianceThresholdBase):
    id: UUID
    org_id: UUID
    created_at: datetime
    updated_at: datetime


class ComplianceThresholdResponse(BaseModel):
    """Single scope threshold view — includes configured flag for unconfigured scopes."""
    scope: str
    threshold_tco2e: float | None = None
    configured: bool


class ThresholdUpsertRequest(BaseModel):
    thresholds: list[ComplianceThresholdCreate]


class TargetUpdateRequest(BaseModel):
    baseline_year: int | None = Field(None, ge=1990, le=2100)
    target_reduction_pct: float | None = Field(None, ge=0, le=100)
    net_zero_target_year: int | None = Field(None, ge=2020, le=2100)


class ScopeBreakdown(BaseModel):
    scope: str
    current_tco2e: float
    threshold_tco2e: float | None
    pct_of_threshold: float | None
    configured: bool


class MonthlyEmissions(BaseModel):
    scope1: float
    scope2: float
    scope3: float
    total: float


class AlertCounts(BaseModel):
    low: int
    medium: int
    high: int
    critical: int


class ComplianceStatus(BaseModel):
    status: str  # compliant | warning | critical | unconfigured
    compliance_pct: float
    sustainability_score: float
    scope_breakdown: list[ScopeBreakdown]
    current_month: MonthlyEmissions
    previous_month: MonthlyEmissions
    pct_change: dict[str, float]
    active_alerts_count: AlertCounts
    last_evaluated_at: datetime


class AlertBase(BaseModel):
    alert_type: str
    severity: str
    status: str
    title: str
    message: str
    scope: str | None = None
    metric_value: float | None = None
    threshold_value: float | None = None
    recommendations: list[Any] = []
    period_month: date


class AlertResponse(BaseSchema, AlertBase):
    id: UUID
    org_id: UUID
    triggered_at: datetime
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None
    created_at: datetime


class ComplianceReportRequest(BaseModel):
    period_start: date | None = None
    period_end: date | None = None
