from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx
from fastapi import FastAPI
from sqlalchemy import text

from app.config import get_settings
from app.database import create_engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.database = create_engine()
    yield
    await app.state.database.dispose()


app = FastAPI(
    title="Recall API",
    version="0.1.0",
    description="Evidence-backed support-case analysis.",
    lifespan=lifespan,
)


@app.get("/api/v1/health")
async def health() -> dict[str, object]:
    settings = get_settings()
    checks: dict[str, str] = {
        "api": "ready",
        "postgres": "unavailable",
        "qdrant": "unavailable",
        "corpus": "not_indexed",
        "provider": "configured" if settings.generation_provider == "mock" or settings.gemini_api_key else "not_configured",
    }

    try:
        async with app.state.database.connect() as connection:
            await connection.execute(text("SELECT 1"))
        checks["postgres"] = "ready"
    except Exception:
        pass

    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{settings.qdrant_url}/readyz")
            if response.is_success:
                checks["qdrant"] = "ready"
    except httpx.HTTPError:
        pass

    ready = checks["postgres"] == "ready" and checks["qdrant"] == "ready"
    return {"status": "ready" if ready else "degraded", "checks": checks}

