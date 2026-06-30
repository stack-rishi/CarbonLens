"""
Compliance API endpoints.
"""
from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import CurrentUser, get_current_user, require_role
from backend.core.db import get_db
from backend.models.models import Alert, ComplianceThreshold, Organization, Report
from backend.models.schemas import (
    AlertResponse,
    ComplianceReportRequest,
    ComplianceThresholdResponse,
    Report as ReportSchema,
    TargetUpdateRequest,
    ThresholdUpsertRequest,
)
from backend.services import alert_service, compliance_service
from backend.workers.tasks import compile_report_task

router = APIRouter()


# ── Compliance Status ──────────────────────────────────────────────────────────

@router.get("/compliance/status")
async def get_compliance_status(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Any:
    """Get full compliance status including sustainability score and scope breakdown."""
    return await compliance_service.get_compliance_status(
        org_id=uuid.UUID(current_user.org_id),
        db=db,
    )


# ── Thresholds ─────────────────────────────────────────────────────────────────

@router.get("/compliance/thresholds", response_model=list[ComplianceThresholdResponse])
async def get_thresholds(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Any:
    """Return all 4 scope thresholds, marking unconfigured ones with configured=false."""
    org_id = uuid.UUID(current_user.org_id)
    result = await db.execute(
        select(ComplianceThreshold).where(ComplianceThreshold.org_id == org_id)
    )
    rows = {t.scope: t.threshold_tco2e for t in result.scalars().all()}

    response = []
    for scope in ["1", "2", "3", "total"]:
        if scope in rows:
            response.append({
                "scope": scope,
                "threshold_tco2e": rows[scope],
                "configured": True,
            })
        else:
            response.append({
                "scope": scope,
                "threshold_tco2e": None,
                "configured": False,
            })
    return response


@router.put("/compliance/thresholds")
async def upsert_thresholds(
    payload: ThresholdUpsertRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(["admin", "analyst"])),
) -> Any:
    """Upsert compliance thresholds for org (admin/analyst only)."""
    org_id = uuid.UUID(current_user.org_id)

    for t in payload.thresholds:
        # Check if exists
        result = await db.execute(
            select(ComplianceThreshold).where(
                ComplianceThreshold.org_id == org_id,
                ComplianceThreshold.scope == t.scope,
            )
        )
        existing = result.scalars().first()

        if existing:
            existing.threshold_tco2e = t.threshold_tco2e
        else:
            db.add(ComplianceThreshold(
                id=uuid.uuid4(),
                org_id=org_id,
                scope=t.scope,
                threshold_tco2e=t.threshold_tco2e,
            ))

    await db.commit()
    return {"status": "ok", "upserted": len(payload.thresholds)}


# ── Targets ────────────────────────────────────────────────────────────────────

@router.put("/compliance/targets")
async def update_targets(
    payload: TargetUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(["admin", "analyst"])),
) -> Any:
    """Update org-level reduction targets (baseline year, reduction %, net zero year)."""
    org_id = uuid.UUID(current_user.org_id)
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalars().first()

    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    if payload.baseline_year is not None:
        org.baseline_year = payload.baseline_year
    if payload.target_reduction_pct is not None:
        org.target_reduction_pct = payload.target_reduction_pct
    if payload.net_zero_target_year is not None:
        org.net_zero_target_year = payload.net_zero_target_year

    await db.commit()
    return {
        "status": "ok",
        "baseline_year": org.baseline_year,
        "target_reduction_pct": org.target_reduction_pct,
        "net_zero_target_year": org.net_zero_target_year,
    }


# ── Manual Evaluate ────────────────────────────────────────────────────────────

@router.post("/compliance/evaluate")
async def evaluate_compliance(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Any:
    """
    Manually trigger a synchronous compliance evaluation.
    Returns fresh compliance status + all newly created/updated alerts.
    Used as the "Recalculate Now" button in the UI.
    """
    org_id = uuid.UUID(current_user.org_id)

    # Run alert evaluation synchronously (NOT background — per spec)
    new_or_updated = await alert_service.evaluate_and_generate_alerts(org_id, db)

    # Fetch fresh compliance status after evaluation
    fresh_status = await compliance_service.get_compliance_status(org_id, db)

    return {
        "status": fresh_status,
        "new_or_updated_alerts": [
            {
                "id": str(a.id),
                "alert_type": a.alert_type,
                "severity": a.severity,
                "status": a.status,
                "title": a.title,
                "scope": a.scope,
                "triggered_at": a.triggered_at.isoformat() if a.triggered_at else None,
            }
            for a in new_or_updated
        ],
    }


# ── Alerts ─────────────────────────────────────────────────────────────────────

@router.get("/alerts", response_model=list[AlertResponse])
async def list_alerts(
    alert_status: str | None = Query(None, alias="status"),
    severity: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Any:
    """List alerts with optional status/severity filters, paginated, newest first."""
    org_id = uuid.UUID(current_user.org_id)
    stmt = (
        select(Alert)
        .where(Alert.org_id == org_id)
        .order_by(Alert.triggered_at.desc())
    )

    if alert_status:
        stmt = stmt.where(Alert.status == alert_status)
    if severity:
        stmt = stmt.where(Alert.severity == severity)

    offset = (page - 1) * limit
    stmt = stmt.limit(limit).offset(offset)

    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/alerts/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Any:
    """Get a single alert with full recommendation detail."""
    org_id = uuid.UUID(current_user.org_id)
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.org_id == org_id)
    )
    alert = result.scalars().first()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return alert


@router.patch("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(["admin", "analyst"])),
) -> Any:
    """Mark an alert as acknowledged."""
    from datetime import datetime

    org_id = uuid.UUID(current_user.org_id)
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.org_id == org_id)
    )
    alert = result.scalars().first()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    alert.status = "acknowledged"
    alert.acknowledged_at = datetime.utcnow()
    await db.commit()
    return {"status": "acknowledged", "alert_id": str(alert_id)}


@router.patch("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(["admin", "analyst"])),
) -> Any:
    """Mark an alert as resolved."""
    from datetime import datetime

    org_id = uuid.UUID(current_user.org_id)
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.org_id == org_id)
    )
    alert = result.scalars().first()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    alert.status = "resolved"
    alert.resolved_at = datetime.utcnow()
    await db.commit()
    return {"status": "resolved", "alert_id": str(alert_id)}


# ── Compliance Report Generation ───────────────────────────────────────────────

@router.post("/compliance/report/generate", response_model=ReportSchema, status_code=status.HTTP_201_CREATED)
async def generate_compliance_report(
    payload: ComplianceReportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(["admin", "analyst"])),
) -> Any:
    """
    Generate a compliance PDF report asynchronously.
    Reuses the same polling mechanism as sustainability reports.
    """
    org_id = uuid.UUID(current_user.org_id)
    today = date.today()
    period_start = payload.period_start or today.replace(day=1)
    period_end = payload.period_end or today

    report = Report(
        id=uuid.uuid4(),
        org_id=org_id,
        generated_by=uuid.UUID(current_user.id),
        period_start=period_start,
        period_end=period_end,
        status="pending",
        report_type="compliance",
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    # Queue to background worker — same pattern as reports.py
    background_tasks.add_task(compile_report_task, report.id)

    return report
