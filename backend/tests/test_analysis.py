import pytest

from app.analysis import AnalysisService
from app.config import Settings
from app.generation import GeneratedAnswer, GeneratedStep, GenerationError, GenerationProvider
from app.retrieval import RetrievedChunk
from app.schemas import TicketAnalyzeRequest


class StubRetriever:
    def __init__(self, evidence: list[RetrievedChunk]) -> None:
        self.evidence = evidence

    def retrieve(self, query: str) -> list[RetrievedChunk]:
        return self.evidence


class FailingRetriever:
    def retrieve(self, query: str) -> list[RetrievedChunk]:
        raise RuntimeError("vector store unavailable")


class StubProvider(GenerationProvider):
    name = "mock"
    model = "stub"

    def __init__(self, answer: GeneratedAnswer | None = None, fail: bool = False) -> None:
        self.answer = answer
        self.fail = fail

    async def generate(
        self, ticket: str, evidence: list[RetrievedChunk]
    ) -> GeneratedAnswer:
        if self.fail:
            raise GenerationError("failed")
        assert self.answer is not None
        return self.answer


def _evidence(score: float = 0.99) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id="postgresql-vacuum:001",
        source_id="postgresql-vacuum",
        title="PostgreSQL: Routine Vacuuming",
        heading="Safe response to rapid disk growth",
        url="https://www.postgresql.org/docs/current/routine-vacuuming.html",
        text="Measure growth before scheduling disruptive maintenance.",
        corpus_version="recall-test",
        dense_score=0.8,
        sparse_score=8.0,
        rerank_score=score,
    )


def _answer(citations: list[str]) -> GeneratedAnswer:
    return GeneratedAnswer(
        category="Storage and maintenance",
        summary="The evidence supports a measured storage investigation.",
        steps=[
            GeneratedStep(
                title="Measure growth",
                instruction="Compare table, index, WAL, temporary-file, and log growth.",
                citations=citations,
            )
        ],
        missing_signals=[],
        conflicts=[],
        answerable=True,
    )


def _answer_with_missing_signal() -> GeneratedAnswer:
    answer = _answer(["postgresql-vacuum:001"])
    return answer.model_copy(update={"missing_signals": ["Database logs from the incident window"]})


def _request() -> TicketAnalyzeRequest:
    return TicketAnalyzeRequest(
        subject="Disk growth",
        description="The database volume is growing faster than expected.",
        product_area="PostgreSQL maintenance",
    )


@pytest.mark.asyncio
async def test_supported_case_returns_cited_draft() -> None:
    provider = StubProvider(_answer(["postgresql-vacuum:001"]))
    service = AnalysisService(
        Settings(generation_provider="mock"),
        retriever=StubRetriever([_evidence()]),
        provider_factory=lambda settings: provider,
    )

    result = await service.analyze(_request())

    assert result.action == "draft"
    assert result.steps[0].citations == ["postgresql-vacuum:001"]
    assert result.confidence.label == "strong"


@pytest.mark.asyncio
async def test_unknown_citation_forces_escalation() -> None:
    provider = StubProvider(_answer(["invented:999"]))
    service = AnalysisService(
        Settings(generation_provider="mock"),
        retriever=StubRetriever([_evidence()]),
        provider_factory=lambda settings: provider,
    )

    result = await service.analyze(_request())

    assert result.action == "escalate"
    assert result.steps == []
    assert any("citations" in reason for reason in result.escalation_rationale)


@pytest.mark.asyncio
async def test_weak_evidence_forces_escalation_even_with_valid_citation() -> None:
    provider = StubProvider(_answer(["postgresql-vacuum:001"]))
    service = AnalysisService(
        Settings(generation_provider="mock"),
        retriever=StubRetriever([_evidence(score=0.02)]),
        provider_factory=lambda settings: provider,
    )

    result = await service.analyze(_request())

    assert result.action == "escalate"
    assert result.confidence.label == "weak"


@pytest.mark.asyncio
async def test_provider_failure_returns_safe_escalation() -> None:
    provider = StubProvider(fail=True)
    service = AnalysisService(
        Settings(generation_provider="mock"),
        retriever=StubRetriever([_evidence()]),
        provider_factory=lambda settings: provider,
    )

    result = await service.analyze(_request())

    assert result.action == "escalate"
    assert result.steps == []
    assert "provider failed" in result.escalation_rationale[0]


@pytest.mark.asyncio
async def test_retrieval_outage_returns_safe_escalation() -> None:
    service = AnalysisService(
        Settings(generation_provider="mock"),
        retriever=FailingRetriever(),
        provider_factory=lambda settings: StubProvider(fail=True),
    )

    result = await service.analyze(_request())

    assert result.action == "escalate"
    assert result.evidence == []
    assert result.corpus_version == "unavailable"
    assert "Retrieval is unavailable" in result.escalation_rationale[0]


@pytest.mark.asyncio
async def test_missing_required_signal_forces_escalation() -> None:
    provider = StubProvider(_answer_with_missing_signal())
    service = AnalysisService(
        Settings(generation_provider="mock"),
        retriever=StubRetriever([_evidence()]),
        provider_factory=lambda settings: provider,
    )

    result = await service.analyze(_request())

    assert result.action == "escalate"
    assert result.missing_signals == ["Database logs from the incident window"]
    assert any("missing" in reason for reason in result.escalation_rationale)


@pytest.mark.asyncio
async def test_explicitly_missing_incident_evidence_escalates_before_generation() -> None:
    service = AnalysisService(
        Settings(generation_provider="mock"),
        retriever=StubRetriever([_evidence()]),
        provider_factory=lambda settings: StubProvider(fail=True),
    )
    request = TicketAnalyzeRequest(
        subject="Connection resets with missing telemetry",
        description=(
            "Clients reported resets, but no timestamps, PostgreSQL logs, or network "
            "telemetry were retained from the incident window."
        ),
        product_area="PostgreSQL connectivity",
    )

    result = await service.analyze(request)

    assert result.action == "escalate"
    assert result.provider == "mock"
    assert "Timestamp-aligned server and network telemetry" in result.missing_signals
