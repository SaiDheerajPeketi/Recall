from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TicketAnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    subject: str = Field(min_length=3, max_length=160)
    description: str = Field(min_length=10, max_length=8_000)
    product_area: str | None = Field(default=None, max_length=80)


class ResolutionStep(BaseModel):
    title: str
    instruction: str
    citations: list[str]


class EvidenceItem(BaseModel):
    chunk_id: str
    source_id: str
    title: str
    heading: str
    url: str
    excerpt: str
    relevance: float
    dense_score: float | None
    sparse_score: float | None


class ConfidenceFactors(BaseModel):
    evidence_strength: float = Field(ge=0, le=1)
    relevance: float = Field(ge=0, le=1)
    source_diversity: float = Field(ge=0, le=1)
    retrieval_agreement: float = Field(ge=0, le=1)
    citation_coverage: float = Field(ge=0, le=1)
    label: Literal["strong", "sufficient", "weak"]
    threshold: float = Field(ge=0, le=1)


class TicketAnalysisResponse(BaseModel):
    analysis_id: str
    category: str
    summary: str
    steps: list[ResolutionStep]
    evidence: list[EvidenceItem]
    confidence: ConfidenceFactors
    action: Literal["draft", "escalate"]
    escalation_rationale: list[str]
    missing_signals: list[str]
    corpus_version: str
    provider: Literal["gemini", "ollama", "mock"]
    provider_model: str
    latency_ms: int


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    analysis_id: str = Field(pattern=r"^[0-9a-f-]{36}$")
    helpfulness: Literal["helpful", "not_helpful"]
    accepted: bool
    correction: str | None = Field(default=None, max_length=2_000)
    comment: str | None = Field(default=None, max_length=1_000)
    minutes_saved: float | None = Field(default=None, ge=0, le=480)

    @model_validator(mode="after")
    def require_feedback_text_when_not_helpful(self) -> "FeedbackRequest":
        if self.helpfulness == "not_helpful" and not (self.correction or self.comment):
            raise ValueError("A correction or comment is required when feedback is not helpful")
        return self


class FeedbackResponse(BaseModel):
    status: Literal["recorded"]


class DemoTicket(BaseModel):
    id: str
    subject: str
    description: str
    product_area: str
    expected_action: Literal["draft", "escalate"]

