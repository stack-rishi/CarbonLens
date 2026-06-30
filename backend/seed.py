import asyncio
import math
import random
import uuid
from datetime import date, timedelta

import bcrypt
from sqlalchemy import func, select
from supabase import create_client

from backend.core.config import settings
from backend.core.db import AsyncSessionLocal
from backend.models.models import (
    ComplianceThreshold,
    EmissionRecord,
    Organization,
    Supplier,
    SupplyChainEdge,
    User,
)


async def seed_data() -> None:
    print("Starting database seeding...")
    async with AsyncSessionLocal() as db:
        # 1. Create Organization: Acme Corp
        org_stmt = select(Organization).where(Organization.name == "Acme Corp")
        res = await db.execute(org_stmt)
        org = res.scalars().first()

        if not org:
            org = Organization(
                id=uuid.uuid4(),
                name="Acme Corp",
                sector="manufacturing",
                country="IN",
                plan="enterprise",
                baseline_year=2023,
                target_reduction_pct=20.0,
                net_zero_target_year=2030,
            )
            db.add(org)
            await db.flush()
            print(f"Created Organization: {org.name} ({org.id})")
        else:
            # Update existing org with new fields
            org.baseline_year = 2023
            org.target_reduction_pct = 20.0
            org.net_zero_target_year = 2030
            await db.flush()
            print(f"Organization Acme Corp already exists ({org.id}), updated fields")

        # 2. Create Admin User
        user_email = "admin@acmecorp.com"
        user_stmt = select(User).where(User.email == user_email)
        res = await db.execute(user_stmt)
        admin_user = res.scalars().first()

        if not admin_user:
            # Create auth user via Supabase
            try:
                supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
                auth_response = supabase.auth.admin.create_user({
                    "email": user_email,
                    "password": "password123",
                    "email_confirm": True
                })
                auth_user_id = auth_response.user.id
            except Exception as e:
                print(f"Failed to create Supabase auth user (maybe already exists or no credentials): {e}")
                auth_user_id = str(uuid.uuid4())  # SECURITY FIX: random UUID, not hardcoded

            admin_user = User(
                id=uuid.UUID(auth_user_id),
                org_id=org.id,
                email=user_email,
                password_hash=bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode("utf-8"),
                role="admin"
            )
            db.add(admin_user)
            await db.flush()
            print(f"Created Admin User: {admin_user.email} ({admin_user.id})")
        else:
            print(f"Admin User already exists ({admin_user.id})")

        # 3. Create Suppliers
        suppliers_data = [
            {"name": "Indo Steel Ltd", "country": "IN", "sector": "steel", "factor": 1.85, "esg": 72.5, "lat": 22.5726, "lng": 88.3639},
            {"name": "Euro Logistics GmbH", "country": "DE", "sector": "transport", "factor": 0.10621, "esg": 88.0, "lat": 50.1109, "lng": 8.6821},
            {"name": "Nippon Electronics", "country": "JP", "sector": "electronics", "factor": 1.25, "esg": 81.2, "lat": 35.6762, "lng": 139.6503},
            {"name": "Texas Plastics Inc", "country": "US", "sector": "plastics", "factor": 2.50, "esg": 64.0, "lat": 29.7604, "lng": -95.3698},
            {"name": "UK Power Solutions", "country": "GB", "sector": "energy", "factor": 0.2071, "esg": 92.5, "lat": 51.5074, "lng": -0.1278},
        ]

        db_suppliers = []
        for s in suppliers_data:
            s_stmt = select(Supplier).where(Supplier.name == s["name"], Supplier.org_id == org.id)
            res = await db.execute(s_stmt)
            supplier = res.scalars().first()

            if not supplier:
                supplier = Supplier(
                    id=uuid.uuid4(),
                    org_id=org.id,
                    name=s["name"],
                    country=s["country"],
                    sector=s["sector"],
                    emission_factor_kg_per_unit=s["factor"],
                    esg_score=s["esg"],
                    lat=s["lat"],
                    lng=s["lng"]
                )
                db.add(supplier)
                await db.flush()
                print(f"Created Supplier: {supplier.name}")
            db_suppliers.append(supplier)

        # 4. Create 24 Months of Emission Records
        today = date.today()
        start_year = today.year - 2 if today.month > 1 else today.year - 3
        start_month = (today.month - 1) % 12 + 1

        current_date = date(start_year, start_month, 1)

        # Check if emission records already exist
        rec_stmt = select(EmissionRecord).where(EmissionRecord.org_id == org.id)
        res = await db.execute(rec_stmt)
        existing_recs = res.scalars().all()

        if not existing_recs:
            print("Generating 24 months of historical emission records...")
            records_to_add = []

            for month_idx in range(24):
                period_start = current_date
                if period_start.month == 12:
                    next_month = date(period_start.year + 1, 1, 1)
                else:
                    next_month = date(period_start.year, period_start.month + 1, 1)
                period_end = next_month - timedelta(days=1)

                trend = 1.0 + (month_idx * 0.015)
                seasonality = 1.0 + 0.15 * math.sin((period_start.month - 4) * math.pi / 6)

                for idx, supplier in enumerate(db_suppliers):
                    base_amount = 5.0 + (idx * 3.5)
                    amount = base_amount * trend * seasonality * random.uniform(0.9, 1.1)

                    scope = "3"
                    category = "purchased_goods"

                    if supplier.name == "UK Power Solutions":
                        scope = "2"
                        category = "electricity"
                    elif supplier.name == "Euro Logistics GmbH":
                        scope = "3"
                        category = "downstream_transport"
                    elif idx % 5 == 0:
                        scope = "1"
                        category = "stationary_combustion"

                    records_to_add.append(
                        EmissionRecord(
                            org_id=org.id,
                            supplier_id=supplier.id,
                            scope=scope,
                            category=category,
                            amount_tco2e=round(amount, 2),
                            period_start=period_start,
                            period_end=period_end,
                            source="automatic_erp" if idx % 2 == 0 else "manual"
                        )
                    )

                current_date = next_month

            db.add_all(records_to_add)
            await db.flush()
            print(f"Generated {len(records_to_add)} monthly emission records.")

        # 5. Create Supply Chain Edges
        edge_stmt = select(SupplyChainEdge).where(SupplyChainEdge.org_id == org.id)
        res = await db.execute(edge_stmt)
        existing_edges = res.scalars().all()

        if not existing_edges:
            print("Connecting supply chain network edges...")

            s_map = {s.name: s for s in db_suppliers}

            edges_to_create = [
                {"from": "Indo Steel Ltd", "to": "Nippon Electronics", "mode": "sea", "dist": 6000.0, "wt": 150.0},
                {"from": "Nippon Electronics", "to": "Texas Plastics Inc", "mode": "air", "dist": 10500.0, "wt": 12.0},
                {"from": "Texas Plastics Inc", "to": "Euro Logistics GmbH", "mode": "sea", "dist": 8200.0, "wt": 45.0},
                {"from": "Euro Logistics GmbH", "to": "Indo Steel Ltd", "mode": "road", "dist": 1200.0, "wt": 80.0},
            ]

            for edge_data in edges_to_create:
                from_supp = s_map.get(edge_data["from"])
                to_supp = s_map.get(edge_data["to"])

                if from_supp and to_supp:
                    edge = SupplyChainEdge(
                        org_id=org.id,
                        from_supplier_id=from_supp.id,
                        to_supplier_id=to_supp.id,
                        transport_mode=edge_data["mode"],
                        distance_km=edge_data["dist"],
                        weight_tonnes=edge_data["wt"]
                    )
                    db.add(edge)
            print("Supply chain edges connected.")

        # ── 6. Seed Compliance Thresholds ──────────────────────────────────────
        print("Seeding compliance thresholds...")

        # Compute average monthly totals per scope from seeded data
        # Group by month and scope, then average across all months
        monthly_scope_result = await db.execute(
            select(
                func.date_trunc("month", EmissionRecord.period_start).label("month"),
                EmissionRecord.scope,
                func.sum(EmissionRecord.amount_tco2e).label("total"),
            )
            .where(EmissionRecord.org_id == org.id)
            .group_by("month", EmissionRecord.scope)
        )
        monthly_rows = monthly_scope_result.fetchall()

        # Compute averages per scope
        scope_monthly: dict[str, list[float]] = {"1": [], "2": [], "3": []}
        for row in monthly_rows:
            if row.scope in scope_monthly and row.total:
                scope_monthly[row.scope].append(float(row.total))

        def avg(vals: list[float]) -> float:
            return sum(vals) / len(vals) if vals else 0.0

        avg_s1 = avg(scope_monthly["1"])
        avg_s2 = avg(scope_monthly["2"])
        avg_s3 = avg(scope_monthly["3"])
        avg_total = avg_s1 + avg_s2 + avg_s3

        # Compute thresholds: 1.15x for s1/s2, 1.10x for s3, 1.12x for total
        # But also check current month — if all are below threshold, deliberately set one below current
        curr_month_start = today.replace(day=1)
        curr_month_result = await db.execute(
            select(
                EmissionRecord.scope,
                func.sum(EmissionRecord.amount_tco2e).label("total"),
            )
            .where(
                EmissionRecord.org_id == org.id,
                EmissionRecord.period_start >= curr_month_start,
            )
            .group_by(EmissionRecord.scope)
        )
        curr_month = {row.scope: float(row.total or 0) for row in curr_month_result}
        _curr_total = sum(curr_month.values())  # noqa: F841

        thresholds_to_seed = {
            "1": avg_s1 * 1.15 if avg_s1 > 0 else 10.0,
            "2": avg_s2 * 1.15 if avg_s2 > 0 else 10.0,
            "3": avg_s3 * 1.10 if avg_s3 > 0 else 10.0,
            "total": avg_total * 1.12 if avg_total > 0 else 50.0,
        }

        # Force one threshold to breach so we get a demo alert
        for scope, total in curr_month.items():
            if total > 0:
                thresholds_to_seed[scope] = total * 0.9  # Set 10% below current
                break

        # Ensure at least one scope shows warning/critical for demo
        # Set scope 3 threshold slightly below current month scope-3 value if it's not already exceeded
        curr_s3 = curr_month.get("3", 0)
        if curr_s3 > 0 and thresholds_to_seed["3"] > curr_s3:
            thresholds_to_seed["3"] = curr_s3 * 0.90  # Set 10% below current -> will trigger alert
            print(f"Adjusted Scope 3 threshold to {thresholds_to_seed['3']:.2f} tCO2e (below current {curr_s3:.2f}) for demo realism")

        for scope_label, threshold_val in thresholds_to_seed.items():
            thresh_stmt = select(ComplianceThreshold).where(
                ComplianceThreshold.org_id == org.id,
                ComplianceThreshold.scope == scope_label,
            )
            res = await db.execute(thresh_stmt)
            existing_thresh = res.scalars().first()

            if existing_thresh:
                existing_thresh.threshold_tco2e = round(threshold_val, 3)
                print(f"Updated Scope {scope_label} threshold: {threshold_val:.3f} tCO2e")
            else:
                db.add(ComplianceThreshold(
                    id=uuid.uuid4(),
                    org_id=org.id,
                    scope=scope_label,
                    threshold_tco2e=round(threshold_val, 3),
                ))
                print(f"Created Scope {scope_label} threshold: {threshold_val:.3f} tCO2e")

        await db.commit()
        print("Compliance thresholds seeded.")

        # 7. Run initial alert evaluation so there are alerts in the DB for the demo
        print("Running initial alert evaluation...")
        from backend.services import alert_service
        async with AsyncSessionLocal() as alert_db:
            try:
                alerts = await alert_service.evaluate_and_generate_alerts(org.id, alert_db)
                print(f"Generated {len(alerts)} alerts from initial evaluation.")
            except Exception as e:
                print(f"Alert evaluation warning (non-fatal): {e}")

        print("Database seeding completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed_data())
