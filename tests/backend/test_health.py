from fastapi.testclient import TestClient

from shred.main import create_app


def test_health_reports_version() -> None:
    response = TestClient(create_app()).get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}
