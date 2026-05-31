from pathlib import Path

from app.evaluation import action_metrics, load_cases, retrieval_scores, tune_threshold
from app.retrieval import RetrievedChunk


def _chunk(chunk_id: str, source_id: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        source_id=source_id,
        title="Source",
        heading="Heading",
        url="https://example.com",
        text="Evidence",
        corpus_version="recall-test",
        rerank_score=0.9,
    )


def test_committed_dataset_has_expected_locked_split() -> None:
    candidates = [
        Path("/app/evaluation/cases.jsonl"),
        Path(__file__).parents[2] / "evaluation" / "cases.jsonl",
    ]
    cases_path = next(path for path in candidates if path.exists())

    development = load_cases(cases_path, "dev", None)
    test = load_cases(cases_path, "test", None)

    assert len(development) == 20
    assert len(test) == 60
    assert len({case.id for case in development + test}) == 80


def test_retrieval_scores_use_top_five_and_expected_sources() -> None:
    evidence = [
        _chunk("other:000", "other"),
        _chunk("wanted:000", "wanted"),
        _chunk("wanted:001", "wanted"),
        _chunk("extra:000", "extra"),
        _chunk("last:000", "last"),
        _chunk("wanted:002", "wanted"),
    ]

    scores = retrieval_scores(evidence, ["wanted"])

    assert scores == {"precision_at_5": 0.4, "recall_at_5": 1.0, "mrr": 0.5}


def test_action_metrics_treat_escalation_as_positive_class() -> None:
    rows = [
        {"expected_action": "escalate", "predicted_action": "escalate"},
        {"expected_action": "escalate", "predicted_action": "draft"},
        {"expected_action": "draft", "predicted_action": "escalate"},
        {"expected_action": "draft", "predicted_action": "draft"},
    ]

    metrics = action_metrics(rows)

    assert metrics["accuracy"] == 0.5
    assert metrics["precision"] == 0.5
    assert metrics["recall"] == 0.5
    assert metrics["confusion_matrix"]["true_escalate"] == {
        "predicted_escalate": 1,
        "predicted_draft": 1,
    }


def test_threshold_tuning_prefers_recall_gate_then_accuracy() -> None:
    rows = [
        {
            "expected_action": "draft",
            "predicted_action": "draft",
            "hard_escalation": False,
            "evidence_strength": 0.8,
        },
        {
            "expected_action": "escalate",
            "predicted_action": "draft",
            "hard_escalation": False,
            "evidence_strength": 0.4,
        },
    ]

    result = tune_threshold(rows)

    assert result["selected"]["threshold"] > 0.4
    assert result["selected"]["accuracy"] == 1.0
