from dataclasses import replace

from app.retrieval import RetrievedChunk, reciprocal_rank_fusion, select_diverse


def _chunk(chunk_id: str, source_id: str, **scores: float) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        source_id=source_id,
        title=f"Title {source_id}",
        heading="Resolution",
        url=f"https://example.test/{source_id}",
        text=f"Evidence {chunk_id}",
        corpus_version="test",
        **scores,
    )


def test_rrf_rewards_chunks_found_by_both_searches() -> None:
    dense = [
        _chunk("dense-only", "a", dense_score=0.9),
        _chunk("shared", "b", dense_score=0.8),
    ]
    sparse = [
        _chunk("shared", "b", sparse_score=12.0),
        _chunk("sparse-only", "c", sparse_score=11.0),
    ]

    fused = reciprocal_rank_fusion(dense, sparse)

    assert fused[0].chunk_id == "shared"
    assert fused[0].dense_score == 0.8
    assert fused[0].sparse_score == 12.0
    assert fused[0].fused_score > fused[1].fused_score


def test_diversity_prefers_distinct_sources_before_second_passage() -> None:
    ranked = [
        replace(_chunk("a-1", "a"), rerank_score=0.99),
        replace(_chunk("a-2", "a"), rerank_score=0.98),
        replace(_chunk("b-1", "b"), rerank_score=0.90),
        replace(_chunk("c-1", "c"), rerank_score=0.80),
    ]

    selected = select_diverse(ranked, limit=4)

    assert [chunk.chunk_id for chunk in selected] == ["a-1", "b-1", "c-1", "a-2"]

