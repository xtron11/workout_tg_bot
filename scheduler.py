from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from models import appointments_table
from database import async_engine
from datetime import datetime, timedelta
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

def start_scheduler(bot):
    scheduler = AsyncIOScheduler(timezone=pytz.timezone("Asia/Almaty"))  # UTC+5 Казахстан
    scheduler.add_job(
        send_reminders,
        trigger=CronTrigger(hour=22, minute=28, timezone=pytz.timezone("Asia/Almaty")),
        args=[bot]
    )
    scheduler.start()