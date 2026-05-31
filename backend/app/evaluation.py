from __future__ import annotations

import argparse
import asyncio
import json
import logging
import math
import platform
import statistics
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable, Literal

import numpy as np

from app.analysis import AnalysisService
from app.config import Settings
from app.generation import GenerationProvider, create_provider
from app.retrieval import HybridRetriever, RetrievedChunk
from app.schemas import TicketAnalyzeRequest, TicketAnalysisResponse


@dataclass(frozen=True)
class EvaluationCase:
    id: str
    split: Literal["dev", "test"]
    subject: str
    description: str
    product_area: str
    expected_sources: list[str]
    expected_action: Literal["draft", "escalate"]
    tags: list[str]

    @property
    def query(self) -> str:
        return "\n".join([self.subject, self.product_area, self.description])

    def request(self) -> TicketAnalyzeRequest:
        return TicketAnalyzeRequest(
            subject=self.subject,
            description=self.description,
            product_area=self.product_area,
        )


class FixedRetriever:
    def __init__(self, evidence: list[RetrievedChunk]) -> None:
        self.evidence = evidence

    def retrieve(self, query: str) -> list[RetrievedChunk]:
        return self.evidence


def load_cases(path: Path, split: str, limit: int | None) -> list[EvaluationCase]:
    cases: list[EvaluationCase] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            case = EvaluationCase(**json.loads(raw))
        except (TypeError, json.JSONDecodeError) as error:
            raise ValueError(f"Invalid evaluation case on line {line_number}") from error
        if split == "all" or case.split == split:
            cases.append(case)
    if limit is not None:
        cases = cases[:limit]
    return cases


def _mean(values: Iterable[float]) -> float:
    items = list(values)
    return round(statistics.fmean(items), 4) if items else 0.0


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    return round(ordered[index], 2)


def retrieval_scores(
    evidence: list[RetrievedChunk], expected_sources: list[str]
) -> dict[str, float] | None:
    if not expected_sources:
        return None
    relevant = set(expected_sources)
    top_five = evidence[:5]
    relevant_passages = sum(1 for item in top_five if item.source_id in relevant)
    retrieved_sources = {item.source_id for item in top_five}
    reciprocal_rank = 0.0
    for rank, item in enumerate(top_five, 1):
        if item.source_id in relevant:
            reciprocal_rank = 1 / rank
            break
    return {
        "precision_at_5": relevant_passages / 5,
        "recall_at_5": len(retrieved_sources & relevant) / len(relevant),
        "mrr": reciprocal_rank,
    }


def action_metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    tp = tn = fp = fn = 0
    for row in rows:
        expected = row["expected_action"] == "escalate"
        predicted = row["predicted_action"] == "escalate"
        if expected and predicted:
            tp += 1
        elif not expected and not predicted:
            tn += 1
        elif not expected and predicted:
            fp += 1
        else:
            fn += 1
    total = tp + tn + fp + fn
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "accuracy": round((tp + tn) / total, 4) if total else 0.0,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "confusion_matrix": {
            "true_escalate": {"predicted_escalate": tp, "predicted_draft": fn},
            "true_draft": {"predicted_escalate": fp, "predicted_draft": tn},
        },
    }


def tune_threshold(rows: list[dict[str, object]]) -> dict[str, object]:
    candidates: list[dict[str, float]] = []
    for step in range(25, 86):
        threshold = step / 100
        adjusted: list[dict[str, object]] = []
        for row in rows:
            predicted = (
                bool(row["hard_escalation"])
                or float(row["evidence_strength"]) < threshold
            )
            adjusted.append(
                {
                    "expected_action": row["expected_action"],
                    "predicted_action": "escalate" if predicted else "draft",
                }
            )
        metrics = action_metrics(adjusted)
        candidates.append(
            {
                "threshold": threshold,
                "accuracy": float(metrics["accuracy"]),
                "escalation_f1": float(metrics["f1"]),
                "escalation_recall": float(metrics["recall"]),
            }
        )
    best = max(
        candidates,
        key=lambda item: (
            item["escalation_recall"] >= 0.9,
            item["accuracy"],
            item["escalation_f1"],
            -abs(item["threshold"] - 0.55),
        ),
    )
    return {"selected": best, "candidates": candidates}


def _cosine(left: np.ndarray, right: np.ndarray) -> float:
    denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
    return float(np.dot(left, right) / denominator) if denominator else 0.0


def claim_checks(
    response: TicketAnalysisResponse,
    evidence: list[RetrievedChunk],
    retriever: HybridRetriever,
) -> list[dict[str, object]]:
    by_id = {item.chunk_id: item for item in evidence}
    checks: list[dict[str, object]] = []
    for index, step in enumerate(response.steps, 1):
        cited = [by_id[citation] for citation in step.citations if citation in by_id]
        valid_citations = bool(step.citations) and len(cited) == len(step.citations)
        similarity = 0.0
        if cited:
            support = "\n".join(item.text for item in cited)
            vectors = list(retriever.dense_model.embed([step.instruction, support]))
            similarity = _cosine(vectors[0], vectors[1])
        checks.append(
            {
                "step": index,
                "valid_citations": valid_citations,
                "semantic_support": round(similarity, 4),
                "faithful": valid_citations and similarity >= 0.45,
            }
        )
    return checks


async def evaluate(
    settings: Settings,
    cases: list[EvaluationCase],
    latency_runs: int,
    request_delay_ms: int,
) -> dict[str, object]:
    retriever = HybridRetriever(settings)
    provider: GenerationProvider = create_provider(settings)
    rows: list[dict[str, object]] = []
    retrieval_metric_rows: list[dict[str, float]] = []
    claim_rows: list[dict[str, object]] = []

    for case in cases:
        retrieval_started = time.perf_counter()
        evidence = await asyncio.to_thread(retriever.retrieve, case.query)
        retrieval_latency = round((time.perf_counter() - retrieval_started) * 1000, 2)
        scores = retrieval_scores(evidence, case.expected_sources)
        if scores:
            retrieval_metric_rows.append(scores)

        service = AnalysisService(
            settings,
            retriever=FixedRetriever(evidence),
            provider_factory=lambda _settings, value=provider: value,
        )
        request = case.request()
        provider_attempted = bool(evidence) and not AnalysisService._explicit_case_gaps(request)
        response = await service.analyze(request)
        claims = claim_checks(response, evidence, retriever)
        claim_rows.extend(claims)
        threshold_only = "Evidence strength is below the tuned answer threshold."
        hard_escalation = response.action == "escalate" and any(
            reason != threshold_only for reason in response.escalation_rationale
        )
        rows.append(
            {
                "id": case.id,
                "tags": case.tags,
                "expected_sources": case.expected_sources,
                "retrieved_chunks": [item.chunk_id for item in evidence],
                "retrieved_sources": [item.source_id for item in evidence],
                "retrieval_latency_ms": retrieval_latency,
                "retrieval": scores,
                "expected_action": case.expected_action,
                "predicted_action": response.action,
                "evidence_strength": response.confidence.evidence_strength,
                "hard_escalation": hard_escalation,
                "citation_coverage": response.confidence.citation_coverage,
                "claims": claims,
                "analysis_latency_ms": response.latency_ms,
                "escalation_rationale": response.escalation_rationale,
                "provider_failure": any(
                    "provider failed" in reason.lower()
                    for reason in response.escalation_rationale
                ),
                "provider_attempted": provider_attempted,
            }
        )
        if request_delay_ms:
            await asyncio.sleep(request_delay_ms / 1000)

    retrieval_metrics = {
        "evaluated_cases": len(retrieval_metric_rows),
        "precision_at_5": _mean(row["precision_at_5"] for row in retrieval_metric_rows),
        "recall_at_5": _mean(row["recall_at_5"] for row in retrieval_metric_rows),
        "mrr": _mean(row["mrr"] for row in retrieval_metric_rows),
        "latency_p50_ms": _percentile(
            [float(row["retrieval_latency_ms"]) for row in rows], 0.5
        ),
        "latency_p95_ms": _percentile(
            [float(row["retrieval_latency_ms"]) for row in rows], 0.95
        ),
    }
    quality_metrics = {
        "claim_level_faithfulness": _mean(
            1.0 if bool(row["faithful"]) else 0.0 for row in claim_rows
        ),
        "citation_coverage": _mean(
            1.0 if bool(row["valid_citations"]) else 0.0 for row in claim_rows
        ),
        "response_citation_coverage": _mean(
            float(row["citation_coverage"])
            for row in rows
            if row["predicted_action"] == "draft"
        ),
        "evaluated_claims": len(claim_rows),
        "faithfulness_method": (
            "A claim passes when every cited chunk exists in the retrieved context and the "
            "local BGE embedding cosine similarity between the step and its cited text is at least 0.45."
        ),
    }

    successful_provider_rows = [row for row in rows if not row["provider_failure"]]
    provider_failures = len(rows) - len(successful_provider_rows)
    provider_attempts = sum(1 for row in rows if row["provider_attempted"])

    latency: dict[str, object] | None = None
    if latency_runs:
        benchmark_case = next(case for case in cases if case.expected_action == "draft")
        benchmark_service = AnalysisService(
            settings,
            retriever=retriever,
            provider_factory=lambda _settings, value=provider: value,
        )
        await benchmark_service.analyze(benchmark_case.request())
        if request_delay_ms:
            await asyncio.sleep(request_delay_ms / 1000)
        samples: list[float] = []
        actions: list[str] = []
        benchmark_provider_failures = 0
        for _ in range(latency_runs):
            result = await benchmark_service.analyze(benchmark_case.request())
            samples.append(float(result.latency_ms))
            actions.append(result.action)
            benchmark_provider_failures += int(
                any(
                    "provider failed" in reason.lower()
                    for reason in result.escalation_rationale
                )
            )
            if request_delay_ms:
                await asyncio.sleep(request_delay_ms / 1000)
        latency = {
            "case_id": benchmark_case.id,
            "warmup_requests": 1,
            "measured_requests": latency_runs,
            "p50_ms": _percentile(samples, 0.5),
            "p95_ms": _percentile(samples, 0.95),
            "min_ms": round(min(samples), 2),
            "max_ms": round(max(samples), 2),
            "drafts": actions.count("draft"),
            "escalations": actions.count("escalate"),
            "provider_failures": benchmark_provider_failures,
            "samples_ms": samples,
        }

    return {
        "metadata": {
            "generated_at": datetime.now(UTC).isoformat(),
            "provider": settings.generation_provider,
            "model": provider.model,
            "corpus_collection": settings.qdrant_collection,
            "evidence_threshold": settings.evidence_threshold,
            "request_delay_ms": request_delay_ms,
            "case_count": len(cases),
            "machine": {
                "platform": platform.platform(),
                "machine": platform.machine(),
                "processor": platform.processor() or "not reported by container",
                "python": platform.python_version(),
            },
        },
        "metrics": {
            "retrieval": retrieval_metrics,
            "quality": quality_metrics,
            "provider_availability": {
                "attempted_requests": provider_attempts,
                "successful_responses": provider_attempts - provider_failures,
                "provider_failures": provider_failures,
                "success_rate": round(
                    (provider_attempts - provider_failures) / provider_attempts, 4
                )
                if provider_attempts
                else 1.0,
            },
            "escalation": {
                "end_to_end": action_metrics(rows),
                "provider_success_only": action_metrics(successful_provider_rows),
            },
            "warm_latency": latency,
        },
        "threshold_tuning": tune_threshold(rows),
        "cases": rows,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the reproducible Recall evaluation")
    parser.add_argument("--cases", type=Path, default=Path("/app/evaluation/cases.jsonl"))
    parser.add_argument("--split", choices=["dev", "test", "all"], default="test")
    parser.add_argument("--provider", choices=["mock", "gemini", "ollama"], default="mock")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--latency-runs", type=int, default=0)
    parser.add_argument("--request-delay-ms", type=int, default=0)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


async def main() -> None:
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("google_genai").setLevel(logging.WARNING)
    args = parse_args()
    cases = load_cases(args.cases, args.split, args.limit)
    if not cases:
        raise SystemExit("No evaluation cases matched the requested split")
    settings = Settings(generation_provider=args.provider)
    report = await evaluate(settings, cases, args.latency_runs, args.request_delay_ms)
    output = args.output or Path(
        f"/app/evaluation/results/{args.split}-{args.provider}.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    summary = {
        "output": str(output),
        "cases": len(cases),
        "retrieval": report["metrics"]["retrieval"],
        "quality": report["metrics"]["quality"],
        "escalation": report["metrics"]["escalation"],
        "warm_latency": report["metrics"]["warm_latency"],
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
