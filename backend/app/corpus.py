from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from fastembed import SparseTextEmbedding, TextEmbedding
from qdrant_client import QdrantClient, models

from app.config import Settings

TOKEN_PATTERN = re.compile(r"\S+")
HEADING_PATTERN = re.compile(r"^#{1,6}\s+.+$", re.MULTILINE)
POINT_NAMESPACE = uuid.UUID("91ecf74e-9009-41b3-9bad-856839bd0ee5")


@dataclass(frozen=True)
class SourceDocument:
    id: str
    title: str
    url: str
    license: str
    retrieved_at: str
    path: Path
    content_sha256: str
    content: str


@dataclass(frozen=True)
class CorpusChunk:
    id: str
    source_id: str
    title: str
    url: str
    license: str
    retrieved_at: str
    content_sha256: str
    heading: str
    text: str


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_sources(manifest_path: Path) -> list[SourceDocument]:
    entries = json.loads(manifest_path.read_text(encoding="utf-8"))
    root = manifest_path.parent
    documents: list[SourceDocument] = []
    seen_ids: set[str] = set()

    for entry in entries:
        source_id = entry["id"]
        if source_id in seen_ids:
            raise ValueError(f"Duplicate source id: {source_id}")
        seen_ids.add(source_id)

        source_path = root / entry["path"]
        raw = source_path.read_bytes()
        actual_hash = _sha256(raw)
        expected_hash = entry["content_sha256"]
        if actual_hash != expected_hash:
            raise ValueError(
                f"Content hash mismatch for {source_id}: expected {expected_hash}, got {actual_hash}"
            )

        documents.append(
            SourceDocument(
                id=source_id,
                title=entry["title"],
                url=entry["url"],
                license=entry["license"],
                retrieved_at=entry["retrieved_at"],
                path=source_path,
                content_sha256=expected_hash,
                content=raw.decode("utf-8"),
            )
        )

    return documents


def _sections(content: str) -> list[tuple[str, str]]:
    matches = list(HEADING_PATTERN.finditer(content))
    if not matches:
        return [("Document", content.strip())]

    sections: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        heading = match.group(0).lstrip("#").strip()
        body = content[match.end() : end].strip()
        if body:
            sections.append((heading, body))
    return sections


def _window_words(text: str, maximum: int = 500, overlap: int = 60) -> Iterable[str]:
    words = TOKEN_PATTERN.findall(text)
    if len(words) <= maximum:
        yield " ".join(words)
        return

    step = maximum - overlap
    for start in range(0, len(words), step):
        window = words[start : start + maximum]
        if window:
            yield " ".join(window)
        if start + maximum >= len(words):
            break


def chunk_sources(documents: Iterable[SourceDocument]) -> list[CorpusChunk]:
    chunks: list[CorpusChunk] = []
    for document in documents:
        index = 0
        for heading, body in _sections(document.content):
            contextual_text = f"{document.title}\n{heading}\n\n{body}"
            for window in _window_words(contextual_text):
                chunks.append(
                    CorpusChunk(
                        id=f"{document.id}:{index:03d}",
                        source_id=document.id,
                        title=document.title,
                        url=document.url,
                        license=document.license,
                        retrieved_at=document.retrieved_at,
                        content_sha256=document.content_sha256,
                        heading=heading,
                        text=window,
                    )
                )
                index += 1
    return chunks


def corpus_version(chunks: Iterable[CorpusChunk]) -> str:
    digest = hashlib.sha256()
    for chunk in sorted(chunks, key=lambda item: item.id):
        digest.update(chunk.id.encode("utf-8"))
        digest.update(chunk.content_sha256.encode("ascii"))
        digest.update(_sha256(chunk.text.encode("utf-8")).encode("ascii"))
    return f"recall-{digest.hexdigest()[:16]}"


def _collection_version(client: QdrantClient, collection_name: str) -> str | None:
    if not client.collection_exists(collection_name):
        return None
    points, _ = client.scroll(collection_name=collection_name, limit=1, with_payload=True)
    if not points or not points[0].payload:
        return None
    value = points[0].payload.get("corpus_version")
    return str(value) if value else None


def index_corpus(settings: Settings) -> dict[str, object]:
    documents = load_sources(settings.source_manifest_path)
    chunks = chunk_sources(documents)
    version = corpus_version(chunks)
    client = QdrantClient(url=settings.qdrant_url, timeout=60)

    if _collection_version(client, settings.qdrant_collection) == version:
        return {"status": "unchanged", "version": version, "chunks": len(chunks)}

    if client.collection_exists(settings.qdrant_collection):
        client.delete_collection(settings.qdrant_collection)

    dense_model = TextEmbedding(model_name=settings.dense_embedding_model)
    sparse_model = SparseTextEmbedding(model_name=settings.sparse_embedding_model)
    texts = [chunk.text for chunk in chunks]
    dense_vectors = list(dense_model.embed(texts))
    sparse_vectors = list(sparse_model.embed(texts))

    dense_size = len(dense_vectors[0])
    client.create_collection(
        collection_name=settings.qdrant_collection,
        vectors_config={
            "dense": models.VectorParams(size=dense_size, distance=models.Distance.COSINE)
        },
        sparse_vectors_config={
            "sparse": models.SparseVectorParams(modifier=models.Modifier.IDF)
        },
    )

    points: list[models.PointStruct] = []
    for chunk, dense, sparse in zip(chunks, dense_vectors, sparse_vectors, strict=True):
        points.append(
            models.PointStruct(
                id=str(uuid.uuid5(POINT_NAMESPACE, chunk.id)),
                vector={
                    "dense": dense.tolist(),
                    "sparse": models.SparseVector(
                        indices=sparse.indices.tolist(),
                        values=sparse.values.tolist(),
                    ),
                },
                payload={
                    "chunk_id": chunk.id,
                    "source_id": chunk.source_id,
                    "title": chunk.title,
                    "heading": chunk.heading,
                    "url": chunk.url,
                    "license": chunk.license,
                    "retrieved_at": chunk.retrieved_at,
                    "content_sha256": chunk.content_sha256,
                    "text": chunk.text,
                    "corpus_version": version,
                },
            )
        )

    client.upsert(collection_name=settings.qdrant_collection, points=points, wait=True)
    return {"status": "indexed", "version": version, "chunks": len(chunks)}

