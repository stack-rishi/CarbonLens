import asyncio
import math
import random
import uuid
from datetime import date, timedelta

import bcrypt
from sqlalchemy import select
from supabase import create_client

from backend.core.config import settings
from backend.core.db import AsyncSessionLocal
from backend.models.models import (
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
                plan="enterprise"
            )
            db.add(org)
            await db.flush()
            print(f"Created Organization: {org.name} ({org.id})")
        else:
            print(f"Organization Acme Corp already exists ({org.id})")

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
                password_hash=bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode("utf-8"),  # SECURITY FIX: store hashed password
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
        # We generate monthly records for the past 24 months
        today = date.today()
        # Start 24 months ago, align with beginning of that month
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
            
            # Generate records month by month
            for month_idx in range(24):
                # Calculate start/end of current month
                period_start = current_date
                if period_start.month == 12:
                    next_month = date(period_start.year + 1, 1, 1)
                else:
                    next_month = date(period_start.year, period_start.month + 1, 1)
                period_end = next_month - timedelta(days=1)

                # Upward trend factor (e.g., grows slightly over 24 months)
                trend = 1.0 + (month_idx * 0.015)
                # Seasonal factor (higher in winter/summer due to HVAC, lowest in spring/autumn)
                # Max seasonality in January (month 1) and July (month 7)
                seasonality = 1.0 + 0.15 * math.sin((period_start.month - 4) * math.pi / 6)

                # Generate records per supplier
                for idx, supplier in enumerate(db_suppliers):
                    # Random scope distribution
                    # Supplier 1: Steel (Scope 3, high emissions)
                    # Supplier 2: Transport (Scope 3, mid emissions)
                    # Supplier 5: Energy (Scope 2, mid emissions)
                    
                    base_amount = 5.0 + (idx * 3.5)
                    amount = base_amount * trend * seasonality * random.uniform(0.9, 1.1)

                    # Distribute Scopes
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

                # Advance to next month
                current_date = next_month

            db.add_all(records_to_add)
            await db.flush()
            print(f"Generated {len(records_to_add)} monthly emission records.")

        # 5. Create Supply Chain Edges
        # Connect suppliers in a logistics graph
        # Indo Steel -> Nippon Electronics -> Texas Plastics -> Euro Logistics -> Acme Corp
        edge_stmt = select(SupplyChainEdge).where(SupplyChainEdge.org_id == org.id)
        res = await db.execute(edge_stmt)
        existing_edges = res.scalars().all()

        if not existing_edges:
            print("Connecting supply chain network edges...")
            
            # Map suppliers by name
            s_map = {s.name: s for s in db_suppliers}
            
            edges_to_create = [
                # Indo Steel -> Nippon Electronics
                {"from": "Indo Steel Ltd", "to": "Nippon Electronics", "mode": "sea", "dist": 6000.0, "wt": 150.0},
                # Nippon Electronics -> Texas Plastics Inc
                {"from": "Nippon Electronics", "to": "Texas Plastics Inc", "mode": "air", "dist": 10500.0, "wt": 12.0},
                # Texas Plastics Inc -> Euro Logistics GmbH
                {"from": "Texas Plastics Inc", "to": "Euro Logistics GmbH", "mode": "sea", "dist": 8200.0, "wt": 45.0},
                # Euro Logistics GmbH -> Acme Corp (sells/delivers to manufacturer)
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
            
            await db.commit()
            print("Supply chain edges connected successfully.")
        else:
            await db.commit()
            print("Supply chain edges already exist.")

        print("Database seeding completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed_data())
