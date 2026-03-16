from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert

from models import metadata_obj, workers_table, appointments_table, available_slots_table
from database import async_engine

async def create_tables():
    async with async_engine.begin() as conn:
        #await conn.run_sync(metadata_obj.drop_all)
        await conn.run_sync(metadata_obj.create_all)
    print("✅ Таблицы успешно пересозданы")

async def insert_user(tg_id: int, username: str, age: int):
    async with async_engine.connect() as conn:
        stmt = insert(workers_table).values(
            tg_id=tg_id,
            username=username,
            age=age
        ).on_conflict_do_nothing(index_elements=['tg_id'])
        await conn.execute(stmt)
        await conn.commit()

async def insert_appointment(user_tg_id: int, username: str, day: str, time: str):
    async with async_engine.connect() as conn:
        # Вставляем именно в appointments_table!
        stmt = insert(appointments_table).values(
            user_tg_id=user_tg_id,
            username=username,
            date=day,
            time=time 
        )
        await conn.execute(stmt)
        await conn.commit()

async def get_user(tg_id: int):
    async with async_engine.connect() as conn:
        query = select(workers_table).where(workers_table.c.tg_id == tg_id)
        result = await conn.execute(query)
        return result.fetchone()

async def get_user_appointments(tg_id: int):
    async with async_engine.connect() as conn:
        query = select(appointments_table).where(
            appointments_table.c.user_tg_id == tg_id
        ).order_by(appointments_table.c.id.desc())
        result = await conn.execute(query)
        return result.fetchall()

# Функция для админа: добавляет слот в базу
async def add_available_slot(day: str, time: str):
    async with async_engine.connect() as conn:
        stmt = insert(available_slots_table).values(day=day, time=time)
        await conn.execute(stmt)
        await conn.commit()

# Функция для юзера: достает уникальные дни, которые добавил админ
async def get_unique_days_from_db():
    async with async_engine.connect() as conn:
        # SELECT DISTINCT day FROM available_slots WHERE is_taken = False
        query = select(available_slots_table.c.day).where(available_slots_table.c.is_taken == False).distinct()
        result = await conn.execute(query)
        return [row[0] for row in result.fetchall()]

# Функция для юзера: достает время для конкретного дня
async def get_times_for_day_from_db(day: str):
    async with async_engine.connect() as conn:
        query = select(available_slots_table.c.time).where(
            available_slots_table.c.day == day,
            available_slots_table.c.is_taken == False
        )
        result = await conn.execute(query)
        return [row[0] for row in result.fetchall()]
    
async def delete_slot_from_db(day: str, time: str):
    async with async_engine.connect() as conn:
        query = delete(available_slots_table).where(
            available_slots_table.c.day == day,
            available_slots_table.c.time == time
        )
        await conn.execute(query)
        await conn.commit()

async def delete_appointment_by_id(appointment_id: int):
    async with async_engine.connect() as conn:
        query = delete(appointments_table).where(
            appointments_table.c.id == appointment_id
        )
        await conn.execute(query)
        await conn.commit()

async def get_appointment_by_id(appointment_id: int):
    async with async_engine.connect() as conn:
        query = select(appointments_table).where(
            appointments_table.c.id == appointment_id
        )
        result = await conn.execute(query)
        return result.fetchone()
    
async def get_appointment_by_day(tg_id: int, day: str):
    async with async_engine.connect() as conn:
        query = select(appointments_table).where(
            appointments_table.c.user_tg_id == tg_id,
            appointments_table.c.date == day
        )
        result = await conn.execute(query)
        return result.fetchone()