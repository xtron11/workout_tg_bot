from config import settings
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from logger import logger

# Асинхронный движок для работы с БД
async_engine = create_async_engine(
    url=settings.DATABASE_URL_asyncpg
)

# Проверяем соединение с БД при старте
async def check_db_connection():
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Подключение к БД успешно")
    except Exception as e:
        logger.error(f"Не удалось подключиться к БД: {e}")
        raise  # останавливаем бота если БД недоступна