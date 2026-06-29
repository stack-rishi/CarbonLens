import os
import uuid
from typing import Any

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text

from backend.api.router import router as api_router
from backend.core.config import settings

# Configure structlog
structlog.configure(
    processors=[
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger()

# Create Rate Limiter (SlowAPI)
limiter = Limiter(key_func=get_remote_address)

# Initialize FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url=None,
    openapi_url="/api/v1/openapi.json" if settings.ENVIRONMENT == "development" else None,
)

# Set rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore

# CORS Configuration
origins = [
    settings.FRONTEND_URL,
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID"],
)

# Ensure static directories exist
STATIC_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(STATIC_PATH, exist_ok=True)
os.makedirs(os.path.join(STATIC_PATH, "reports"), exist_ok=True)

# Mount static files (to access generated PDF reports)
app.mount("/static", StaticFiles(directory=STATIC_PATH), name="static")


# Global HTTP Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next: Any) -> Any:
    log = logger.bind(method=request.method, path=request.url.path)
    log.info("request_received")
    try:
        response = await call_next(request)
        log.info("request_completed", status_code=response.status_code)
        return response
    except Exception as e:
        log.error("request_failed", error=str(e))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An unexpected error occurred. Please contact system admin."},
        )

@app.middleware("http")
async def add_security_headers(request: Request, call_next: Any) -> Any:
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: blob:;"
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response

@app.middleware("http")
async def add_request_id(request: Request, call_next: Any) -> Any:
    request_id = str(uuid.uuid4())[:8]
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# Health check endpoint
@app.get("/health", tags=["System"])
async def health() -> Any:
    try:
        # We need an async context for get_db generator.
        # But for simplicity since get_db is a dependency generator, we can just instantiate AsyncSessionLocal.
        from backend.core.db import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "error"
    return {
        "status": "ok" if db_status == "connected" else "degraded",
        "db": db_status,
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }


# Include API Router
app.include_router(api_router, prefix="/api/v1")
