import uuid
from typing import Any

from backend.core.auth import CurrentUser, get_current_user
from backend.core.db import get_db
from backend.models.models import Supplier
from backend.services.optimizer_service import OptimizerService
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

@router.post("/optimize/route")
async def optimize_route(
    payload: dict[str, Any],
    current_user: CurrentUser = Depends(get_current_user),
) -> Any:
    """Optimize transport route."""
    dist = float(payload.get("distance_km", 1000))
    weight = float(payload.get("weight_tonnes", 10))
    comparisons = OptimizerService.calculate_alternative_routes(distance_km=dist, weight_tonnes=weight)
    return {"routes": comparisons}

@router.post("/optimize/suppliers")
async def optimize_suppliers(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Any:
    """Optimize sourcing among suppliers."""
    total_demand = float(payload.get("total_demand_tonnes", 100))
    min_esg = float(payload.get("min_esg_score", 0.0))

    stmt = select(Supplier).where(Supplier.org_id == uuid.UUID(current_user.org_id))
    res = await db.execute(stmt)
    db_suppliers = res.scalars().all()
    
    if not db_suppliers:
        raise HTTPException(status_code=400, detail="No suppliers found")

    solver_inputs = []
    for s in db_suppliers:
        solver_inputs.append({
            "id": str(s.id),
            "name": s.name,
            "capacity_tonnes": total_demand * 0.7,
            "production_emission_factor": s.emission_factor_kg_per_unit,
            "transport_distance_km": 1500.0,
            "transport_mode": "road",
            "esg_score": s.esg_score or 50.0,
        })

    opt_result = OptimizerService.optimize_sourcing(
        suppliers=solver_inputs,
        total_demand_tonnes=total_demand,
        min_esg_score=min_esg,
    )
    return opt_result
