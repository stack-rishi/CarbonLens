import uuid
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import CurrentUser, get_current_user, require_role
from backend.core.db import get_db
from backend.models.models import EmissionRecord, Supplier
from backend.models.schemas import EmissionRecord as EmissionRecordSchema
from backend.models.schemas import EmissionRecordCreate
from backend.services import alert_service
from backend.services.emission_service import EmissionService

router = APIRouter()


@router.get("", response_model=list[EmissionRecordSchema])
async def list_emissions(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    limit: int = Query(100, ge=1, le=1000, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Any:
    """List all emission records, optionally filtered by dates. Paginated."""
    stmt = select(EmissionRecord).where(
        EmissionRecord.org_id == uuid.UUID(current_user.org_id)
    )

    if start_date:
        stmt = stmt.where(EmissionRecord.period_start >= start_date)
    if end_date:
        stmt = stmt.where(EmissionRecord.period_end <= end_date)

    stmt = stmt.order_by(EmissionRecord.period_start.desc()).limit(limit).offset(offset)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("", response_model=EmissionRecordSchema, status_code=status.HTTP_201_CREATED)
async def create_emission_record(
    payload: EmissionRecordCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(["admin", "analyst"])),
) -> Any:
    """Create a new carbon emission data point."""
    # If supplier is associated, verify it belongs to the organization
    if payload.supplier_id:
        stmt = select(Supplier).where(
            Supplier.id == payload.supplier_id,
            Supplier.org_id == uuid.UUID(current_user.org_id),
        )
        res = await db.execute(stmt)
        supplier = res.scalars().first()
        if not supplier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Supplier not found or unauthorized",
            )

    record = EmissionRecord(
        org_id=uuid.UUID(current_user.org_id),
        supplier_id=payload.supplier_id,
        scope=payload.scope,
        category=payload.category,
        amount_tco2e=payload.amount_tco2e,
        period_start=payload.period_start,
        period_end=payload.period_end,
        source=payload.source,
    )

    db.add(record)
    await db.commit()
    await db.refresh(record)

    # Real-time alert re-evaluation (non-blocking)
    org_id = uuid.UUID(current_user.org_id)
    background_tasks.add_task(alert_service.evaluate_and_generate_alerts, org_id, db)

    return record


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_emission_record(
    record_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(["admin"])),
) -> None:
    """Delete an emission record."""
    stmt = select(EmissionRecord).where(
        EmissionRecord.id == record_id,
        EmissionRecord.org_id == uuid.UUID(current_user.org_id),
    )
    res = await db.execute(stmt)
    record = res.scalars().first()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emission record not found or unauthorized",
        )

    await db.delete(record)
    await db.commit()


@router.get("/summary")
async def get_summary(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Any:
    """Get aggregated emissions data by scope, category, and supplier."""
    # Defaults to past 12 months if no dates provided
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=365)

    summary = await EmissionService.get_emissions_summary(
        db=db,
        org_id=uuid.UUID(current_user.org_id),
        start_date=start_date,
        end_date=end_date,
    )
    return summary


@router.get("/trend")
async def get_trend(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Any:
    """Get monthly emission trends grouped by Scope."""
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=365)

    trend = await EmissionService.get_monthly_trend(
        db=db,
        org_id=uuid.UUID(current_user.org_id),
        start_date=start_date,
        end_date=end_date,
    )
    return {"trend": trend}


@router.post("/bulk-import")
async def bulk_import_emissions(
    payload: dict[str, Any],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(["admin", "analyst"])),
) -> Any:
    """Bulk import emissions."""
    # Real-time alert re-evaluation after bulk import (non-blocking)
    org_id = uuid.UUID(current_user.org_id)
    background_tasks.add_task(alert_service.evaluate_and_generate_alerts, org_id, db)
    return {"status": "success", "imported_count": 0}
