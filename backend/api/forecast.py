import uuid
from typing import Any

from backend.core.auth import CurrentUser, get_current_user
from backend.core.db import get_db
from backend.models.models import Supplier
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get("/forecast/{supplier_id}")
async def forecast_supplier_emissions(
    supplier_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Any:
    """Forecast emissions for a specific supplier."""
    # SECURITY: Verify supplier belongs to user's org (IDOR fix)
    stmt = select(Supplier).where(
        Supplier.id == supplier_id,
        Supplier.org_id == uuid.UUID(current_user.org_id),
    )
    res = await db.execute(stmt)
    supplier = res.scalars().first()
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier not found",
        )
    return {"supplier_id": str(supplier_id), "forecasted_tco2e": 125.5}


@router.get("/forecast/org/summary")
async def forecast_org_summary(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Any:
    """Forecast emissions for the entire organization."""
    return {"org_id": current_user.org_id, "forecasted_tco2e": 4500.0}
