import hashlib
import json
from pathlib import Path

import pytest

from app.corpus import chunk_sources, corpus_version, load_sources


def _write_source(tmp_path: Path, content: str, digest: str | None = None) -> Path:
    source_path = tmp_path / "source.md"
    source_path.write_text(content, encoding="utf-8")
    content_hash = digest or hashlib.sha256(content.encode("utf-8")).hexdigest()
    manifest = [
        {
            "id": "source",
            "title": "Source title",
            "url": "https://example.test/source",
            "license": "Test license",
            "retrieved_at": "2026-09-16",
            "path": "source.md",
            "content_sha256": content_hash,
        }
    ]
    manifest_path = tmp_path / "sources.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path


def test_load_sources_rejects_changed_content(tmp_path: Path) -> None:
    manifest_path = _write_source(tmp_path, "# Heading\n\nTrusted content", digest="0" * 64)

    with pytest.raises(ValueError, match="Content hash mismatch"):
        load_sources(manifest_path)


def test_chunking_and_version_are_deterministic(tmp_path: Path) -> None:
    words = " ".join(f"word-{index}" for index in range(720))
    manifest_path = _write_source(tmp_path, f"# Guide\n\n## Resolution\n\n{words}")
    documents = load_sources(manifest_path)

    first = chunk_sources(documents)
    second = chunk_sources(documents)

    assert [chunk.id for chunk in first] == ["source:000", "source:001"]
    assert first == second
    assert corpus_version(first) == corpus_version(second)
    assert len(first[0].text.split()) == 500
    assert first[0].text.split()[-60:] == first[1].text.split()[:60]
