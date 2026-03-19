import asyncio
from aiogram import Bot, Dispatcher, BaseMiddleware
from config import settings
from core import create_tables
from scheduler import start_scheduler
from handlers.user_handlers import user_router
from handlers.admin_handlers import admin_router
from logger import logger
from database import check_db_connection

# Middleware для перехвата всех ошибок
class ErrorMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        try:
            return await handler(event, data)
        except Exception as e:
            logger.error(f"Ошибка при обработке события: {e}", exc_info=True)

async def main():
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()

    # Подключаем обработчик ошибок
    dp.update.middleware(ErrorMiddleware())

    await check_db_connection()  # сначала проверяем БД
    # Создаём таблицы если их нет
    await create_tables()
    logger.info("Таблицы созданы")

    # Запускаем планировщик напоминаний
    start_scheduler(bot)
    logger.info("Планировщик запущен")

    # Важно: admin_router первым — он проверяется раньше user_router
    dp.include_router(admin_router)
    dp.include_router(user_router)

    logger.info("Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен вручную")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")