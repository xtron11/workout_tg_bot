from sqlalchemy import create_engine
from config import settings
from sqlalchemy.ext.asyncio import create_async_engine

sync_engine = create_engine(
    url=settings.DATABASE_URL_psycopg,
    echo=True,
)

async_engine = create_async_engine(
    url = settings.DATABASE_URL_asyncpg
)