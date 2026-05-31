from fastapi.testclient import TestClient

from app.database import feedback
from app.main import app


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
