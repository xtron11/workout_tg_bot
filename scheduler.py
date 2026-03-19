from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from datetime import datetime, timedelta
from models import appointments_table
from database import async_engine
from core import delete_old_slots, delete_old_appointments
from logger import logger

import pytz

scheduler = AsyncIOScheduler()

async def send_reminders(bot):
    # Берём завтрашнюю дату в формате DD.MM
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%d.%m")
    
    async with async_engine.connect() as conn:
        query = select(appointments_table).where(
            appointments_table.c.date == tomorrow
        )
        result = await conn.execute(query)
        appointments = result.fetchall()
    
    for appointment in appointments:
        try:
            await bot.send_message(
                chat_id=appointment.user_tg_id,
                text=(f"🔔 Напоминание!\n"
                      f"Завтра у вас тренировка в {appointment.time}\n"
                      f"Не забудьте! 💪")
            )
        except Exception as e:
            print(f"Не удалось отправить напоминание {appointment.user_tg_id}: {e}")

async def delete_old_records(bot):
    await delete_old_slots()
    await delete_old_appointments()
    logger.info("Старые записи удалены")

def start_scheduler(bot):
    scheduler = AsyncIOScheduler(timezone=pytz.timezone("Asia/Almaty"))
    
    # Напоминания каждый день в 21:00
    scheduler.add_job(
        send_reminders,
        trigger=CronTrigger(hour=21, minute=0, timezone=pytz.timezone("Asia/Almaty")),
        args=[bot]
    )
    
    # Удаление старых записей каждый день в полночь
    scheduler.add_job(
        delete_old_records,
        trigger=CronTrigger(hour=0, minute=0, timezone=pytz.timezone("Asia/Almaty")),
        args=[bot]
    )
    
    scheduler.start()