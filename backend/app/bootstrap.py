import asyncio
import json

from app.config import get_settings
from app.corpus import index_corpus
from app.database import create_engine, create_schema


async def bootstrap() -> None:
    engine = create_engine()
    try:
        await create_schema(engine)
        result = await asyncio.to_thread(index_corpus, get_settings())
        print(json.dumps(result, sort_keys=True))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(bootstrap())
