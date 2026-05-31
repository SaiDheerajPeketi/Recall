from fastapi.testclient import TestClient

from app.main import app


def test_openapi_exposes_health_route() -> None:
    schema = app.openapi()
    assert "/api/v1/health" in schema["paths"]

