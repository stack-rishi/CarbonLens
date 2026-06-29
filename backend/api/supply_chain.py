import uuid
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import CurrentUser, get_current_user
from backend.core.db import get_db
from backend.models.models import EmissionRecord, Supplier, SupplyChainEdge

router = APIRouter()


@router.get("/supply-chain/graph")
async def get_supply_chain_graph(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Any:
    """Get the supply chain graph nodes and edges."""
    org_id = uuid.UUID(current_user.org_id)

    # 1. Fetch all suppliers for the organization
    supp_stmt = select(Supplier).where(Supplier.org_id == org_id)
    supp_res = await db.execute(supp_stmt)
    suppliers = supp_res.scalars().all()

    # 2. Fetch emissions per supplier in the last 30 days
    cutoff_date = date.today() - timedelta(days=30)
    emissions_stmt = (
        select(
            EmissionRecord.supplier_id,
            func.sum(EmissionRecord.amount_tco2e).label("total"),
        )
        .where(
            EmissionRecord.org_id == org_id,
            EmissionRecord.period_start >= cutoff_date,
        )
        .group_by(EmissionRecord.supplier_id)
    )
    em_res = await db.execute(emissions_stmt)
    emissions_map = {
        row.supplier_id: row.total for row in em_res.all() if row.supplier_id
    }

    # 3. Calculate max emissions to scale intensity (0.0 to 1.0)
    max_emissions = max(emissions_map.values()) if emissions_map else 1.0
    if max_emissions == 0.0:
        max_emissions = 1.0

    # 4. Fetch previous 30 days to calculate trend
    prev_cutoff_date = date.today() - timedelta(days=60)
    prev_emissions_stmt = (
        select(
            EmissionRecord.supplier_id,
            func.sum(EmissionRecord.amount_tco2e).label("total"),
        )
        .where(
            EmissionRecord.org_id == org_id,
            EmissionRecord.period_start >= prev_cutoff_date,
            EmissionRecord.period_start < cutoff_date,
        )
        .group_by(EmissionRecord.supplier_id)
    )
    prev_em_res = await db.execute(prev_emissions_stmt)
    prev_emissions_map = {
        row.supplier_id: row.total for row in prev_em_res.all() if row.supplier_id
    }

    # 5. Build nodes list
    nodes = []
    for s in suppliers:
        tco2e = round(emissions_map.get(s.id, 0.0), 2)
        prev_tco2e = prev_emissions_map.get(s.id, 0.0)

        # Calculate trend
        if tco2e > prev_tco2e * 1.05:
            trend = "up"
        elif tco2e < prev_tco2e * 0.95:
            trend = "down"
        else:
            trend = "flat"

        intensity = round(tco2e / max_emissions, 2)

        nodes.append(
            {
                "id": str(s.id),
                "label": s.name,
                "country": s.country or "IN",
                "sector": s.sector or "Unknown",
                "esg_score": s.esg_score or 70.0,
                "tco2e_30d": tco2e,
                "intensity": intensity,
                "trend": trend,
            }
        )

    # 6. Fetch edges
    edges_stmt = select(SupplyChainEdge).where(SupplyChainEdge.org_id == org_id)
    edges_res = await db.execute(edges_stmt)
    db_edges = edges_res.scalars().all()

    edges = []
    for e in db_edges:
        edges.append(
            {
                "id": str(e.id),
                "source": str(e.from_supplier_id),
                "target": str(e.to_supplier_id),
                "transport_mode": e.transport_mode,
                "weight_tonnes": e.weight_tonnes,
            }
        )

    return {"nodes": nodes, "edges": edges}


from backend.models.schemas import SupplyChainEdgeCreate
from backend.models.schemas import SupplyChainEdge as EdgeSchema

@router.post("/supply-chain/edges", response_model=EdgeSchema, status_code=201)
async def create_supply_chain_edge(
    payload: SupplyChainEdgeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Any:
    """Create a new supply chain edge linking two suppliers."""
    edge = SupplyChainEdge(
        org_id=uuid.UUID(current_user.org_id),
        from_supplier_id=payload.from_supplier_id,
        to_supplier_id=payload.to_supplier_id,
        transport_mode=payload.transport_mode,
        distance_km=payload.distance_km,
        weight_tonnes=payload.weight_tonnes,
    )
    db.add(edge)
    await db.commit()
    await db.refresh(edge)
    return edge

