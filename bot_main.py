import asyncio
from aiogram import Bot, Dispatcher
from config import settings
from core import create_tables
from scheduler import start_scheduler
from handlers.user_handlers import user_router
from handlers.admin_handlers import admin_router

async def main():
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()

    await create_tables()

    # Запускаем планировщик
    start_scheduler(bot)
    
    dp.include_router(admin_router)
    dp.include_router(user_router)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())