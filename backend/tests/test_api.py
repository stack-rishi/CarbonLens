import os

import pytest
from httpx import ASGITransport, AsyncClient

# Force test environment so config doesn't raise production guards
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-only-for-ci")


@pytest.mark.anyio
async def test_health_check() -> None:
    """Verify that the FastAPI healthcheck endpoint resolves correctly.

    The /health endpoint will report db='error' in CI (no real Postgres),
    but it should still return 200 with status='degraded' at minimum.
    """
    from backend.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("ok", "degraded")
        assert "version" in data
        assert data["environment"] == "development"
