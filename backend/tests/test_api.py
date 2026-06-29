import pytest
from backend.main import app
from httpx import ASGITransport, AsyncClient


@pytest.mark.anyio
async def test_health_check() -> None:
    """Verify that the FastAPI healthcheck endpoint resolves correctly."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["environment"] == "development"
