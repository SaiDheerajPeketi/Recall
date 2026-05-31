from __future__ import annotations

import asyncio
import re
import time
import uuid
from collections.abc import Callable
from typing import Protocol

from app.config import Settings
from app.generation import GeneratedAnswer, GenerationError, GenerationProvider, create_provider
from app.retrieval import HybridRetriever, RetrievedChunk
from app.schemas import (
    ConfidenceFactors,
    EvidenceItem,
    ResolutionStep,
    TicketAnalysisResponse,
    TicketAnalyzeRequest,
)


class Retriever(Protocol):
    def retrieve(self, query: str) -> list[RetrievedChunk]: ...


class AnalysisService:
    def __init__(
        self,
        settings: Settings,
        retriever: Retriever | None = None,
        provider_factory: Callable[[Settings], GenerationProvider] = create_provider,
    ) -> None:
        self.settings = settings
        self._retriever = retriever
        self._provider_factory = provider_factory

    def _retrieve(self, query: str) -> list[RetrievedChunk]:
        if self._retriever is None:
            self._retriever = HybridRetriever(self.settings)
        return self._retriever.retrieve(query)

    async def analyze(self, request: TicketAnalyzeRequest) -> TicketAnalysisResponse:
        started = time.perf_counter()
        analysis_id = str(uuid.uuid4())
        query = "\n".join(
            value
            for value in [request.subject, request.product_area, request.description]
            if value
        )
        provider_name = self.settings.generation_provider
        provider_model = self._configured_model()

        try:
            evidence = await asyncio.to_thread(self._retrieve, query)
        except Exception:
            return self._escalation(
                analysis_id=analysis_id,
                started=started,
                evidence=[],
                provider_name=provider_name,
                provider_model=provider_model,
                summary="Recall could not retrieve the support corpus for this case.",
                rationale=["Retrieval is unavailable; no safe resolution can be drafted."],
                missing_signals=["Reachable, indexed support corpus"],
            )

        if not evidence:
            return self._escalation(
                analysis_id=analysis_id,
                started=started,
                evidence=[],
                provider_name=provider_name,
                provider_model=provider_model,
                summary="The corpus did not return relevant support evidence for this case.",
                rationale=["No passage cleared the retrieval relevance floor."],
                missing_signals=["Relevant documentation or a matching resolved incident"],
            )

        explicit_gaps = self._explicit_case_gaps(request)
        if explicit_gaps:
            return self._escalation(
                analysis_id=analysis_id,
                started=started,
                evidence=evidence,
                provider_name=provider_name,
                provider_model=provider_model,
                summary="The case explicitly reports missing or conflicting diagnostic evidence.",
                rationale=[
                    "Required incident evidence is absent or internally inconsistent; a safe resolution cannot be drafted."
                ],
                missing_signals=explicit_gaps,
            )

        try:
            provider = self._provider_factory(self.settings)
            provider_name = provider.name
            provider_model = provider.model
            generated = await provider.generate(query, evidence)
        except GenerationError:
            return self._escalation(
                analysis_id=analysis_id,
                started=started,
                evidence=evidence,
                provider_name=provider_name,
                provider_model=provider_model,
                summary="Evidence was retrieved, but the configured model did not return a usable draft.",
                rationale=["The generation provider failed or returned invalid structured output."],
                missing_signals=["Valid structured provider response"],
            )

        return self._finalize(
            analysis_id=analysis_id,
            started=started,
            evidence=evidence,
            provider_name=provider_name,
            provider_model=provider_model,
            generated=generated,
        )

    def _finalize(
        self,
        analysis_id: str,
        started: float,
        evidence: list[RetrievedChunk],
        provider_name: str,
        provider_model: str,
        generated: GeneratedAnswer,
    ) -> TicketAnalysisResponse:
        evidence_ids = {chunk.chunk_id for chunk in evidence}
        step_citations = [citation for step in generated.steps for citation in step.citations]
        invalid_citations = sorted(set(step_citations) - evidence_ids)
        cited_steps = sum(
            1
            for step in generated.steps
            if step.citations and all(citation in evidence_ids for citation in step.citations)
        )
        citation_coverage = cited_steps / len(generated.steps) if generated.steps else 0.0
        confidence = self._confidence(evidence, citation_coverage)
        rationale: list[str] = []

        if not generated.answerable:
            rationale.append("The provider judged the supplied evidence insufficient for a safe answer.")
        if not generated.steps:
            rationale.append("No actionable resolution steps were produced.")
        if invalid_citations:
            rationale.append("One or more citations do not refer to retrieved evidence.")
        if citation_coverage < 1.0:
            rationale.append("Every actionable step must have a valid citation.")
        if generated.conflicts:
            rationale.append("The selected evidence contains unresolved conflicts.")
        if generated.missing_signals:
            rationale.append("Required diagnostic evidence is missing from the case.")
        if confidence.evidence_strength < self.settings.evidence_threshold:
            rationale.append("Evidence strength is below the tuned answer threshold.")

        action = "escalate" if rationale else "draft"
        steps = [] if action == "escalate" else [
            ResolutionStep(
                title=step.title,
                instruction=step.instruction,
                citations=step.citations,
            )
            for step in generated.steps
        ]
        missing_signals = list(generated.missing_signals)
        if action == "escalate" and not missing_signals:
            missing_signals = ["Additional case evidence or validated diagnostic results"]

        return TicketAnalysisResponse(
            analysis_id=analysis_id,
            category=generated.category,
            summary=generated.summary,
            steps=steps,
            evidence=self._evidence_items(evidence),
            confidence=confidence,
            action=action,
            escalation_rationale=rationale,
            missing_signals=missing_signals,
            corpus_version=evidence[0].corpus_version,
            provider=provider_name,
            provider_model=provider_model,
            latency_ms=round((time.perf_counter() - started) * 1000),
        )

    def _escalation(
        self,
        analysis_id: str,
        started: float,
        evidence: list[RetrievedChunk],
        provider_name: str,
        provider_model: str,
        summary: str,
        rationale: list[str],
        missing_signals: list[str],
    ) -> TicketAnalysisResponse:
        return TicketAnalysisResponse(
            analysis_id=analysis_id,
            category="Needs escalation",
            summary=summary,
            steps=[],
            evidence=self._evidence_items(evidence),
            confidence=self._confidence(evidence, 0.0),
            action="escalate",
            escalation_rationale=rationale,
            missing_signals=missing_signals,
            corpus_version=evidence[0].corpus_version if evidence else "unavailable",
            provider=provider_name,
            provider_model=provider_model,
            latency_ms=round((time.perf_counter() - started) * 1000),
        )

    def _confidence(
        self,
        evidence: list[RetrievedChunk],
        citation_coverage: float,
    ) -> ConfidenceFactors:
        relevance = max((chunk.rerank_score for chunk in evidence), default=0.0)
        relevance = max(0.0, min(relevance, 1.0))
        diversity = min(len({chunk.source_id for chunk in evidence}) / 3, 1.0)
        agreement = (
            sum(
                1
                for chunk in evidence
                if chunk.dense_score is not None and chunk.sparse_score is not None
            )
            / len(evidence)
            if evidence
            else 0.0
        )
        strength = (
            0.4 * relevance
            + 0.2 * diversity
            + 0.15 * agreement
            + 0.25 * citation_coverage
        )
        strength = round(max(0.0, min(strength, 1.0)), 4)
        if strength >= 0.8:
            label = "strong"
        elif strength >= self.settings.evidence_threshold:
            label = "sufficient"
        else:
            label = "weak"
        return ConfidenceFactors(
            evidence_strength=strength,
            relevance=round(relevance, 4),
            source_diversity=round(diversity, 4),
            retrieval_agreement=round(agreement, 4),
            citation_coverage=round(citation_coverage, 4),
            label=label,
            threshold=self.settings.evidence_threshold,
        )

    @staticmethod
    def _evidence_items(evidence: list[RetrievedChunk]) -> list[EvidenceItem]:
        return [
            EvidenceItem(
                chunk_id=chunk.chunk_id,
                source_id=chunk.source_id,
                title=chunk.title,
                heading=chunk.heading,
                url=chunk.url,
                excerpt=chunk.text,
                relevance=round(chunk.rerank_score, 4),
                dense_score=round(chunk.dense_score, 4)
                if chunk.dense_score is not None
                else None,
                sparse_score=round(chunk.sparse_score, 4)
                if chunk.sparse_score is not None
                else None,
            )
            for chunk in evidence
        ]

    def _configured_model(self) -> str:
        if self.settings.generation_provider == "gemini":
            return self.settings.gemini_model
        if self.settings.generation_provider == "ollama":
            return self.settings.ollama_model
        return "deterministic-rules-v1"

    @staticmethod
    def _explicit_case_gaps(request: TicketAnalyzeRequest) -> list[str]:
        text = f"{request.subject}\n{request.description}".lower()
        checks = [
            (
                r"\bno\b.{0,120}\b(logs?|timestamps?|telemetry|packet captures?|network metrics?)\b",
                "Timestamp-aligned server and network telemetry",
            ),
            (
                r"\bno\b.{0,120}\b(sql text|query text|execution plan|parameters?|wait events?|statistics)\b",
                "The affected query and execution diagnostics",
            ),
            (
                r"\b(conflicting|conflicts|cannot reconcile|different (?:time )?windows)\b",
                "Reconciled measurements from the same incident window",
            ),
            (
                r"\b(no timestamp alignment|raw (?:sample|evidence).{0,30}(?:missing|unavailable|not available))\b",
                "Raw measurements with a shared timestamp window",
            ),
        ]
        return [label for pattern, label in checks if re.search(pattern, text)]
