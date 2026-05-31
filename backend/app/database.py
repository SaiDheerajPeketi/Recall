from sqlalchemy import Boolean, Column, DateTime, Float, Integer, MetaData, String, Table, Text, func
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.config import get_settings

metadata = MetaData()

feedback = Table(
    "feedback",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("analysis_id", String(36), nullable=False, index=True),
    Column("helpful", Boolean, nullable=False),
    Column("accepted", Boolean, nullable=False),
    Column("correction", Text, nullable=True),
    Column("comment", Text, nullable=True),
    Column("minutes_saved", Float, nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

evaluation_runs = Table(
    "evaluation_runs",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("profile", String(80), nullable=False),
    Column("corpus_version", String(80), nullable=False),
    Column("metrics_json", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)


def create_engine() -> AsyncEngine:
    return create_async_engine(get_settings().database_url, pool_pre_ping=True)


async def create_schema(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(metadata.create_all)
