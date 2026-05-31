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
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash-lite"
    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "qwen3:4b"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
