from fastapi.testclient import TestClient

from elyra_backend.core.app import app


def test_health_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "ok"
    assert data.get("arch") == "braid-v2-skeleton"


