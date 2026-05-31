from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx
from fastapi import FastAPI
from sqlalchemy import text

from app.analysis import AnalysisService
from app.config import get_settings
from app.database import create_engine
from app.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    app.state.database = create_engine()
    app.state.analysis_service = AnalysisService(settings)
    yield
    await app.state.database.dispose()


app = FastAPI(
    title="Recall API",
    version="0.1.0",
    description="Evidence-backed support-case analysis.",
    lifespan=lifespan,
)
app.include_router(router)


@app.get("/api/v1/health")
async def health() -> dict[str, object]:
    settings = get_settings()
    checks: dict[str, str] = {
        "api": "ready",
        "postgres": "unavailable",
        "qdrant": "unavailable",
        "corpus": "not_indexed",
        "provider": "not_configured",
    }

    if settings.generation_provider == "mock":
        checks["provider"] = "ready"
    elif settings.generation_provider == "gemini" and settings.resolved_gemini_api_key:
        checks["provider"] = "ready"

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
                collection = await client.get(
                    f"{settings.qdrant_url}/collections/{settings.qdrant_collection}"
                )
                if collection.is_success:
                    points_count = collection.json().get("result", {}).get("points_count", 0)
                    if points_count > 0:
                        checks["corpus"] = "ready"
            if settings.generation_provider == "ollama":
                provider = await client.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags")
                if provider.is_success:
                    checks["provider"] = "ready"
    except httpx.HTTPError:
        pass

    ready = all(
        checks[name] == "ready"
        for name in ("api", "postgres", "qdrant", "corpus", "provider")
    )
    return {"status": "ready" if ready else "degraded", "checks": checks}
