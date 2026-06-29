from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.emission_factors import get_factor
from backend.models.models import EmissionRecord, Supplier


class EmissionService:
    @staticmethod
    def calculate_transport_emissions(
        weight_tonnes: float, distance_km: float, mode: str
    ) -> float:
        """Calculate transport emissions in tCO2e.

        Formula: weight (tonnes) * distance (km) * factor (kg CO2e/tonne-km) / 1000 (kg/tonne)
        """
        factor = get_factor("transport", mode)
        emissions_kg = weight_tonnes * distance_km * factor
        return float(emissions_kg / 1000.0)

    @staticmethod
    def calculate_energy_emissions(kwh: float, country: str) -> float:
        """Calculate electricity emissions in tCO2e.

        Formula: energy (kWh) * factor (kg CO2e/kWh) / 1000 (kg/tonne)
        """
        factor = get_factor("energy", country)
        emissions_kg = kwh * factor
        return float(emissions_kg / 1000.0)

    @staticmethod
    def calculate_material_emissions(weight_kg: float, material_type: str) -> float:
        """Calculate material production emissions in tCO2e.

        Formula: weight (kg) * factor (kg CO2e/kg) / 1000 (kg/tonne)
        """
        factor = get_factor("material", material_type)
        emissions_kg = weight_kg * factor
        return float(emissions_kg / 1000.0)

    @staticmethod
    async def get_emissions_summary(
        db: AsyncSession, org_id: UUID, start_date: date, end_date: date
    ) -> dict[str, Any]:
        """Aggregate emissions by Scope, Category, and Supplier for an organization."""
        # Query records
        query = select(EmissionRecord).where(
            EmissionRecord.org_id == org_id,
            EmissionRecord.period_start >= start_date,
            EmissionRecord.period_end <= end_date,
        )
        result = await db.execute(query)
        records = result.scalars().all()

        total = 0.0
        by_scope = {"1": 0.0, "2": 0.0, "3": 0.0}
        by_category: dict[str, float] = {}
        by_supplier: dict[str, float] = {}

        # Get supplier names for formatting
        supplier_ids = [r.supplier_id for r in records if r.supplier_id]
        supplier_names = {}
        if supplier_ids:
            supp_result = await db.execute(
                select(Supplier).where(Supplier.id.in_(supplier_ids))
            )
            for s in supp_result.scalars().all():
                supplier_names[s.id] = s.name

        for record in records:
            amt = record.amount_tco2e
            total += amt
            by_scope[record.scope] = by_scope.get(record.scope, 0.0) + amt

            cat = record.category or "uncategorized"
            by_category[cat] = by_category.get(cat, 0.0) + amt

            if record.supplier_id:
                name = supplier_names.get(record.supplier_id, str(record.supplier_id))
                by_supplier[name] = by_supplier.get(name, 0.0) + amt
            else:
                by_supplier["Internal"] = by_supplier.get("Internal", 0.0) + amt

        return {
            "total_tco2e": round(total, 2),
            "by_scope": {k: round(v, 2) for k, v in by_scope.items()},
            "by_category": {k: round(v, 2) for k, v in by_category.items()},
            "by_supplier": {k: round(v, 2) for k, v in by_supplier.items()},
            "record_count": len(records),
        }

    @staticmethod
    async def get_monthly_trend(
        db: AsyncSession, org_id: UUID, start_date: date, end_date: date
    ) -> list[dict[str, Any]]:
        """Return emissions aggregated by year-month."""
        # Custom SQL grouping for cross-database compatibility: extract year and month
        query = (
            select(
                func.date_trunc("month", EmissionRecord.period_start).label("month"),
                func.sum(EmissionRecord.amount_tco2e).label("total"),
                EmissionRecord.scope,
            )
            .where(
                EmissionRecord.org_id == org_id,
                EmissionRecord.period_start >= start_date,
                EmissionRecord.period_end <= end_date,
            )
            .group_by(text("month"), EmissionRecord.scope)
            .order_by("month")
        )

        result = await db.execute(query)
        rows = result.all()

        # Combine items by month
        trend_map: dict[str, dict[str, Any]] = {}
        for row in rows:
            m_date: date = row[0]
            if not m_date:
                continue
            month_str = m_date.strftime("%Y-%m")
            val = float(row[1] or 0.0)
            scope = row[2]

            if month_str not in trend_map:
                trend_map[month_str] = {
                    "month": month_str,
                    "scope_1": 0.0,
                    "scope_2": 0.0,
                    "scope_3": 0.0,
                    "total": 0.0,
                }

            trend_map[month_str][f"scope_{scope}"] = round(val, 2)
            trend_map[month_str]["total"] = round(
                trend_map[month_str]["total"] + val, 2
            )

        return sorted(trend_map.values(), key=lambda x: x["month"])
