from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Sequence

from fastembed import SparseTextEmbedding, TextEmbedding
from flashrank import Ranker, RerankRequest
from qdrant_client import QdrantClient, models

from app.config import Settings


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    source_id: str
    title: str
    heading: str
    url: str
    text: str
    corpus_version: str
    dense_score: float | None = None
    sparse_score: float | None = None
    fused_score: float = 0.0
    rerank_score: float = 0.0


def reciprocal_rank_fusion(
    dense: Sequence[RetrievedChunk],
    sparse: Sequence[RetrievedChunk],
    rank_constant: int = 60,
) -> list[RetrievedChunk]:
    by_id: dict[str, RetrievedChunk] = {}
    scores: Counter[str] = Counter()

    for rank, chunk in enumerate(dense, start=1):
        by_id[chunk.chunk_id] = chunk
        scores[chunk.chunk_id] += 1.0 / (rank_constant + rank)

    for rank, chunk in enumerate(sparse, start=1):
        previous = by_id.get(chunk.chunk_id)
        if previous:
            by_id[chunk.chunk_id] = replace(previous, sparse_score=chunk.sparse_score)
        else:
            by_id[chunk.chunk_id] = chunk
        scores[chunk.chunk_id] += 1.0 / (rank_constant + rank)

    return sorted(
        (replace(chunk, fused_score=scores[chunk_id]) for chunk_id, chunk in by_id.items()),
        key=lambda item: (-item.fused_score, item.chunk_id),
    )


def select_diverse(chunks: Sequence[RetrievedChunk], limit: int = 5) -> list[RetrievedChunk]:
    selected: list[RetrievedChunk] = []
    selected_ids: set[str] = set()
    source_counts: Counter[str] = Counter()

    for chunk in chunks:
        if source_counts[chunk.source_id] == 0:
            selected.append(chunk)
            selected_ids.add(chunk.chunk_id)
            source_counts[chunk.source_id] += 1
            if len(selected) == limit:
                return selected

    for chunk in chunks:
        if chunk.chunk_id in selected_ids or source_counts[chunk.source_id] >= 2:
            continue
        selected.append(chunk)
        selected_ids.add(chunk.chunk_id)
        source_counts[chunk.source_id] += 1
        if len(selected) == limit:
            break

    return selected


def _chunk_from_point(point: models.ScoredPoint, score_field: str) -> RetrievedChunk:
    payload = point.payload or {}
    values = {
        "chunk_id": str(payload["chunk_id"]),
        "source_id": str(payload["source_id"]),
        "title": str(payload["title"]),
        "heading": str(payload["heading"]),
        "url": str(payload["url"]),
        "text": str(payload["text"]),
        "corpus_version": str(payload["corpus_version"]),
        score_field: float(point.score),
    }
    return RetrievedChunk(**values)


class HybridRetriever:
    def __init__(
        self,
        settings: Settings,
        client: QdrantClient | None = None,
        dense_model: TextEmbedding | None = None,
        sparse_model: SparseTextEmbedding | None = None,
        ranker: Ranker | None = None,
    ) -> None:
        self.settings = settings
        self.client = client or QdrantClient(url=settings.qdrant_url, timeout=30)
        self.dense_model = dense_model or TextEmbedding(model_name=settings.dense_embedding_model)
        self.sparse_model = sparse_model or SparseTextEmbedding(
            model_name=settings.sparse_embedding_model
        )
        self.ranker = ranker or Ranker(
            model_name=settings.reranker_model,
            cache_dir=str(Path.home() / ".cache" / "flashrank"),
        )

    def retrieve(self, query: str) -> list[RetrievedChunk]:
        dense_vector = next(self.dense_model.query_embed(query)).tolist()
        sparse_embedding = next(self.sparse_model.query_embed(query))
        sparse_vector = models.SparseVector(
            indices=sparse_embedding.indices.tolist(),
            values=sparse_embedding.values.tolist(),
        )

        dense_points = self.client.query_points(
            collection_name=self.settings.qdrant_collection,
            query=dense_vector,
            using="dense",
            limit=self.settings.retrieval_candidates,
            with_payload=True,
        ).points
        sparse_points = self.client.query_points(
            collection_name=self.settings.qdrant_collection,
            query=sparse_vector,
            using="sparse",
            limit=self.settings.retrieval_candidates,
            with_payload=True,
        ).points

        dense_chunks = [_chunk_from_point(point, "dense_score") for point in dense_points]
        sparse_chunks = [_chunk_from_point(point, "sparse_score") for point in sparse_points]
        fused = reciprocal_rank_fusion(dense_chunks, sparse_chunks)
        reranked = self._rerank(query, fused[: self.settings.rerank_candidates])
        relevant = [
            chunk
            for chunk in reranked
            if chunk.rerank_score >= self.settings.minimum_rerank_score
        ]
        return select_diverse(relevant, self.settings.evidence_limit)

    def _rerank(
        self, query: str, chunks: Sequence[RetrievedChunk]
    ) -> list[RetrievedChunk]:
        if not chunks:
            return []

        passages = [
            {"id": index, "text": chunk.text, "meta_data": {"chunk_id": chunk.chunk_id}}
            for index, chunk in enumerate(chunks)
        ]
        results = self.ranker.rerank(RerankRequest(query=query, passages=passages))
        by_index = {index: chunk for index, chunk in enumerate(chunks)}
        reranked: list[RetrievedChunk] = []
        for result in results:
            index = int(result["id"])
            reranked.append(replace(by_index[index], rerank_score=float(result["score"])))
        return reranked
