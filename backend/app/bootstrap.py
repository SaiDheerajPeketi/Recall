import asyncio

from app.database import create_engine, create_schema


async def bootstrap() -> None:
    engine = create_engine()
    try:
        await create_schema(engine)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(bootstrap())

