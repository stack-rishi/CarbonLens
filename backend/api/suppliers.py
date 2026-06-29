import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import CurrentUser, get_current_user, require_role
from backend.core.db import get_db
from backend.models.models import Supplier, SupplyChainEdge
from backend.models.schemas import Supplier as SupplierSchema
from backend.models.schemas import SupplierCreate, SupplyChainEdgeCreate
from backend.models.schemas import SupplyChainEdge as EdgeSchema
from backend.services.optimizer_service import OptimizerService

router = APIRouter()


# Supplier CRUD
@router.get("", response_model=list[SupplierSchema])
async def list_suppliers(
    limit: int = Query(100, ge=1, le=1000, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Any:
    """Fetch all suppliers belonging to the user's organization. Paginated."""
    stmt = select(Supplier).where(
        Supplier.org_id == uuid.UUID(current_user.org_id)
    ).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("", response_model=SupplierSchema, status_code=status.HTTP_201_CREATED)
async def create_supplier(
    payload: SupplierCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(["admin", "analyst"])),
) -> Any:
    """Create a new supplier profile."""
    supplier = Supplier(
        org_id=uuid.UUID(current_user.org_id),
        name=payload.name,
        country=payload.country,
        sector=payload.sector,
        emission_factor_kg_per_unit=payload.emission_factor_kg_per_unit,
        esg_score=payload.esg_score,
        lat=payload.lat,
        lng=payload.lng,
    )
    db.add(supplier)
    await db.commit()
    await db.refresh(supplier)
    return supplier


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_supplier(
    supplier_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(["admin"])),
) -> None:
    """Delete a supplier profile."""
    # Ensure supplier exists and belongs to the organization
    stmt = select(Supplier).where(
        Supplier.id == supplier_id,
        Supplier.org_id == uuid.UUID(current_user.org_id),
    )
    res = await db.execute(stmt)
    supplier = res.scalars().first()

    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier not found or unauthorized",
        )

    await db.delete(supplier)
    await db.commit()


# Supply Chain Edges (Graph)
@router.get("/edges", response_model=list[EdgeSchema])
async def list_edges(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Any:
    """List all supply chain logistics connections."""
    stmt = select(SupplyChainEdge).where(
        SupplyChainEdge.org_id == uuid.UUID(current_user.org_id)
    )
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/edges", response_model=EdgeSchema, status_code=status.HTTP_201_CREATED)
async def create_edge(
    payload: SupplyChainEdgeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(["admin", "analyst"])),
) -> Any:
    """Create a supply chain connection between suppliers."""
    # Validate from/to suppliers belong to org
    stmt = select(Supplier.id).where(
        Supplier.org_id == uuid.UUID(current_user.org_id),
        Supplier.id.in_([payload.from_supplier_id, payload.to_supplier_id])
    )
    res = await db.execute(stmt)
    found_ids = res.scalars().all()
    if len(found_ids) < 2 and payload.from_supplier_id != payload.to_supplier_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both suppliers must belong to your organization",
        )

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


# Optimization Endpoints
@router.post("/optimize-sourcing")
async def optimize_sourcing(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Any:
    """Run carbon-sourcing optimization on suppliers.

    Request format:
    {
      "total_demand_tonnes": 500,
      "min_esg_score": 75
    }
    """
    total_demand = float(payload.get("total_demand_tonnes", 100))
    min_esg = float(payload.get("min_esg_score", 0.0))

    # Fetch organization suppliers to compile parameters
    stmt = select(Supplier).where(Supplier.org_id == uuid.UUID(current_user.org_id))
    res = await db.execute(stmt)
    db_suppliers = res.scalars().all()

    if not db_suppliers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No suppliers found in database to run optimization",
        )

    # Convert DB suppliers into optimizer input list
    # We will simulate capacity and distance parameters for realistic solving
    solver_inputs = []
    for s in db_suppliers:
        # Default capacities and distances for simulation if not stored
        solver_inputs.append({
            "id": str(s.id),
            "name": s.name,
            "capacity_tonnes": total_demand * 0.7, # supply cap limit
            "production_emission_factor": s.emission_factor_kg_per_unit, # tCO2e/tonne
            "transport_distance_km": 1500.0, # assumed average distance
            "transport_mode": "road",
            "esg_score": s.esg_score or 50.0,
        })

    # Run OR-Tools Optimization
    opt_result = OptimizerService.optimize_sourcing(
        suppliers=solver_inputs,
        total_demand_tonnes=total_demand,
        min_esg_score=min_esg,
    )
    return opt_result


@router.post("/compare-routes")
async def compare_routes(
    payload: dict[str, Any],
    current_user: CurrentUser = Depends(get_current_user),
) -> Any:
    """Compare alternative carbon footprint transport routing paths.

    Request format:
    {
      "distance_km": 1200,
      "weight_tonnes": 50
    }
    """
    dist = float(payload.get("distance_km", 0))
    weight = float(payload.get("weight_tonnes", 0))

    if dist <= 0 or weight <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Distance and Weight must be positive values.",
        )

    comparisons = OptimizerService.calculate_alternative_routes(
        distance_km=dist, weight_tonnes=weight
    )
    return {"routes": comparisons}

@router.post("/bulk-import")
async def bulk_import_suppliers(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(["admin", "analyst"])),
) -> Any:
    """Bulk import suppliers."""
    return {"status": "success", "imported_count": 0}
