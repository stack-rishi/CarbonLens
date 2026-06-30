from backend.api.ai import router as ai_router
from backend.api.auth import router as auth_router
from backend.api.compliance import router as compliance_router
from backend.api.emissions import router as emissions_router
from backend.api.forecast import router as forecast_router
from backend.api.optimize import router as optimize_router
from backend.api.reports import router as reports_router
from backend.api.suppliers import router as suppliers_router
from backend.api.supply_chain import router as supply_chain_router
from fastapi import APIRouter

router = APIRouter()

# Include subrouters
router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
router.include_router(suppliers_router, prefix="/suppliers", tags=["Suppliers"])
router.include_router(emissions_router, prefix="/emissions", tags=["Emissions"])
router.include_router(reports_router, prefix="/reports", tags=["Reports"])
router.include_router(ai_router, prefix="/ai", tags=["AI Conversations"])
router.include_router(supply_chain_router, prefix="", tags=["Supply Chain"])
router.include_router(forecast_router, prefix="", tags=["Forecast"])
router.include_router(optimize_router, prefix="", tags=["Optimize"])
router.include_router(compliance_router, prefix="", tags=["Compliance"])
