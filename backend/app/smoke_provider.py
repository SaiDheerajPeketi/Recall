import asyncio
import json

from app.config import get_settings
from app.generation import create_provider
from app.retrieval import RetrievedChunk


async def smoke_provider() -> None:
    settings = get_settings()
    provider = create_provider(settings)
    evidence = [
        RetrievedChunk(
            chunk_id="postgresql-vacuum:001",
            source_id="postgresql-vacuum",
            title="PostgreSQL: Routine Vacuuming",
            heading="Safe response to rapid disk growth",
            url="https://www.postgresql.org/docs/current/routine-vacuuming.html",
            text=(
                "Identify which objects are growing, distinguish table and index growth from WAL, "
                "temporary files, and logs, then inspect long-running transactions and autovacuum."
            ),
            corpus_version="smoke-test",
            rerank_score=0.99,
        )
    ]
    answer = await provider.generate(
        "Disk use is growing rapidly and autovacuum does not appear to reclaim space.",
        evidence,
    )
    print(
        json.dumps(
            {
                "provider": provider.name,
                "model": provider.model,
                "answerable": answer.answerable,
                "citations": sorted(
                    {citation for step in answer.steps for citation in step.citations}
                ),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    asyncio.run(smoke_provider())

