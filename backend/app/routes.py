from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import insert

from app.database import feedback
from app.schemas import (
    DemoTicket,
    FeedbackRequest,
    FeedbackResponse,
    TicketAnalysisResponse,
    TicketAnalyzeRequest,
)

router = APIRouter(prefix="/api/v1")


DEMO_TICKETS = [
    DemoTicket(
        id="DB-10468",
        subject="Disk space is growing rapidly",
        description=(
            "The orders database volume gained 38 GB in two days. Autovacuum is enabled, "
            "but the team is unsure whether table bloat, WAL retention, or temporary files are responsible."
        ),
        product_area="PostgreSQL maintenance",
        expected_action="draft",
    ),
    DemoTicket(
        id="DB-10469",
        subject="Vector query returns fewer rows after filtering",
        description=(
            "An HNSW cosine search with a category filter requests 20 rows but sometimes returns six. "
            "The same table returns more results when the approximate index is bypassed."
        ),
        product_area="pgvector search",
        expected_action="draft",
    ),
    DemoTicket(
        id="DB-10472",
        subject="Intermittent connection resets with no matching logs",
        description=(
            "The application reports connection reset by peer for roughly five percent of connections. "
            "No database logs or network telemetry from the incident window are available."
        ),
        product_area="PostgreSQL connectivity",
        expected_action="escalate",
    ),
]


@router.post("/tickets/analyze", response_model=TicketAnalysisResponse)
async def analyze_ticket(
    payload: TicketAnalyzeRequest,
    request: Request,
) -> TicketAnalysisResponse:
    return await request.app.state.analysis_service.analyze(payload)


@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_feedback(
    payload: FeedbackRequest,
    request: Request,
) -> FeedbackResponse:
    values = {
        "analysis_id": payload.analysis_id,
        "helpful": payload.helpfulness == "helpful",
        "accepted": payload.accepted,
        "correction": payload.correction,
        "comment": payload.comment,
        "minutes_saved": payload.minutes_saved,
    }
    try:
        async with request.app.state.database.begin() as connection:
            await connection.execute(insert(feedback).values(**values))
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Feedback storage is temporarily unavailable.",
        ) from error
    return FeedbackResponse(status="recorded")


@router.get("/demo-tickets", response_model=list[DemoTicket])
async def demo_tickets() -> list[DemoTicket]:
    return DEMO_TICKETS

