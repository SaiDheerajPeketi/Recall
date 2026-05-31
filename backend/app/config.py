from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Recall"
    environment: str = "local"
    database_url: str = "postgresql+asyncpg://recall:recall-local@localhost:5432/recall"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "recall_support"
    source_manifest_path: Path = Path("../data/sources.json")
    generation_provider: Literal["gemini", "ollama", "mock"] = "gemini"
    dense_embedding_model: str = "BAAI/bge-small-en-v1.5"
    sparse_embedding_model: str = "Qdrant/bm25"
    reranker_model: str = "ms-marco-TinyBERT-L-2-v2"
    retrieval_candidates: int = 30
    rerank_candidates: int = 20
    evidence_limit: int = 5
    minimum_rerank_score: float = 0.01
    evidence_threshold: float = 0.55
    gemini_api_key: str = ""
    google_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "qwen3:4b"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def resolved_gemini_api_key(self) -> str:
        return self.gemini_api_key or self.google_api_key


@lru_cache
def get_settings() -> Settings:
    return Settings()
