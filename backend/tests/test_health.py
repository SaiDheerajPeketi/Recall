import httpx
import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.database import feedback
from app.main import app


class BrokenConnection:
    async def __aenter__(self) -> "BrokenConnection":
        raise RuntimeError("database unavailable")

    async def __aexit__(self, *args: object) -> None:
        return None


class BrokenDatabase:
    def connect(self) -> BrokenConnection:
        return BrokenConnection()


class OfflineClient:
    async def __aenter__(self) -> "OfflineClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def get(self, url: str) -> None:
        raise httpx.ConnectError("service unavailable")


def test_openapi_exposes_health_route() -> None:
    schema = app.openapi()
    assert {
        "/api/v1/health",
        "/api/v1/tickets/analyze",
        "/api/v1/feedback",
        "/api/v1/demo-tickets",
    }.issubset(schema["paths"])


def test_demo_tickets_are_public_and_safe() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/demo-tickets")

    assert response.status_code == 200
    assert len(response.json()) == 3
    assert {ticket["expected_action"] for ticket in response.json()} == {"draft", "escalate"}


def test_feedback_table_has_no_ticket_text_columns() -> None:
    columns = {column.name for column in feedback.columns}

    assert "subject" not in columns
    assert "description" not in columns
    assert "ticket_text" not in columns


@pytest.mark.asyncio
async def test_health_reports_data_service_outages_as_degraded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(app.state, "database", BrokenDatabase(), raising=False)
    monkeypatch.setattr(main_module.httpx, "AsyncClient", lambda **kwargs: OfflineClient())

    result = await main_module.health()

    assert result["status"] == "degraded"
    assert result["checks"]["postgres"] == "unavailable"
    assert result["checks"]["qdrant"] == "unavailable"
    assert result["checks"]["corpus"] == "not_indexed"
