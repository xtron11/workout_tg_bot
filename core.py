import sqlalchemy
from sqlalchemy import select, delete, union
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime

from models import metadata_obj, users_table, appointments_table, available_slots_table
from database import async_engine
from logger import logger

# Создаем все таблицы из models.py
async def create_tables():
    async with async_engine.begin() as conn:
        #await conn.run_sync(metadata_obj.drop_all)
        await conn.run_sync(metadata_obj.create_all)
    logger.info("Таблицы успешно пересозданы")

# Сохраняем пользователя в таблице users
async def insert_user(tg_id: int, first_name: str, last_name: str):
    async with async_engine.connect() as conn:
        stmt = insert(users_table).values(
            tg_id=tg_id,
            first_name=first_name,
            last_name=last_name
        ).on_conflict_do_nothing(index_elements=['tg_id'])
        await conn.execute(stmt)
        await conn.commit()

# Пользователь регистрирует запись
async def insert_appointment(user_tg_id: int, username: str, day: str, time: str):
    async with async_engine.connect() as conn:
        stmt = insert(appointments_table).values(
            user_tg_id=user_tg_id,
            username=username,
            date=day,
            time=time 
        )
        await conn.execute(stmt)
        await conn.commit()

# Запрос пользователя
async def get_user(tg_id: int):
    async with async_engine.connect() as conn:
        query = select(users_table).where(users_table.c.tg_id == tg_id)
        result = await conn.execute(query)
        return result.fetchone()

# Запрос всех пользователей
async def get_all_users():
    async with async_engine.connect() as conn:
        query = select(users_table)
        result = await conn.execute(query)
        return result.fetchall()

# Получаем все записи пользователя по его tg_id
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
    
# Удаляет слот из available_slots когда пользователь записался на это время
async def delete_slot_from_db(day: str, time: str):
    async with async_engine.connect() as conn:
        query = delete(available_slots_table).where(
            available_slots_table.c.day == day,
            available_slots_table.c.time == time
        )
        await conn.execute(query)
        await conn.commit()

# Удаляет свободный слот из available_slots по id (используется админом)
async def delete_slot_by_id(slot_id: int):
    async with async_engine.connect() as conn:
        query = delete(available_slots_table).where(
            available_slots_table.c.id == slot_id
        )
        await conn.execute(query)
        await conn.commit()

# Удаляет запись пользователя из appointments по id
async def delete_appointment_by_id(appointment_id: int):
    async with async_engine.connect() as conn:
        query = delete(appointments_table).where(
            appointments_table.c.id == appointment_id
        )
        await conn.execute(query)
        await conn.commit()

# Получаем запись по id — нужно чтобы знать данные перед удалением
async def get_appointment_by_id(appointment_id: int):
    async with async_engine.connect() as conn:
        query = select(appointments_table).where(
            appointments_table.c.id == appointment_id
        )
        result = await conn.execute(query)
        return result.fetchone()

# Проверяем записан ли пользователь на конкретный день. Защита от двойной записи
async def get_appointment_by_day(tg_id: int, day: str):
    async with async_engine.connect() as conn:
        query = select(appointments_table).where(
            appointments_table.c.user_tg_id == tg_id,
            appointments_table.c.date == day
        )
        result = await conn.execute(query)
        return result.fetchone()

# Получаем все дни из обеих таблиц (свободные + занятые) для админа
async def get_all_days():
    async with async_engine.connect() as conn:
        slots_query = select(available_slots_table.c.day)
        appointments_query = select(appointments_table.c.date)
        combined = union(slots_query, appointments_query)
        result = await conn.execute(combined)
        return result.fetchall()

# Для админа: Объединяем две таблицы для того чтобы админ смог удалять запись / удалять запись пользователя
async def get_slots_and_appointments_by_day(day: str):
    async with async_engine.connect() as conn:
        # Свободные слоты
        free_query = select(
            available_slots_table.c.time,
            sqlalchemy.literal(None).label("username"),
            available_slots_table.c.id.label("id"),  # реальный id из available_slots
            sqlalchemy.literal("free").label("status")
        ).where(available_slots_table.c.day == day)
        
        # Занятые слоты
        taken_query = select(
            appointments_table.c.time,
            appointments_table.c.username,
            appointments_table.c.id,
            sqlalchemy.literal("taken").label("status")
        ).where(appointments_table.c.date == day)
        
        combined = union(free_query, taken_query)
        result = await conn.execute(combined)
        return result.fetchall()

# Берем всех пользователей из БД чтобы прислать им уведомления
async def get_users_for_notification():
    async with async_engine.connect() as conn:
        query = select(users_table.c.tg_id)
        result = await conn.execute(query)
        return [row[0] for row in result.fetchall()]

# Удаляем пользователя из БД   
async def delete_user(tg_id: int):
    async with async_engine.connect() as conn:
        # Сначала получаем все записи пользователя
        query = select(appointments_table).where(
            appointments_table.c.user_tg_id == tg_id
        )
        result = await conn.execute(query)
        appointments = result.fetchall()
        
        # Возвращаем слоты обратно
        for app in appointments:
            await conn.execute(insert(available_slots_table).values(
                day=app.date, time=app.time
            ))
        
        # Удаляем пользователя — CASCADE сам удалит его записи
        await conn.execute(delete(users_table).where(
            users_table.c.tg_id == tg_id
        ))
        await conn.commit()

async def delete_old_slots():
    current_year = datetime.now().year
    today = datetime.now().date()
    
    async with async_engine.connect() as conn:
        # Получаем все слоты
        result = await conn.execute(select(available_slots_table))
        slots = result.fetchall()
        
        for slot in slots:
            try:
                # Преобразуем "19.03" в date(2026, 3, 19)
                slot_date = datetime.strptime(f"{slot.day}.{current_year}", "%d.%m.%Y").date()
                if slot_date < today:
                    await conn.execute(delete(available_slots_table).where(
                        available_slots_table.c.id == slot.id
                    ))
            except ValueError:
                pass  # если формат даты неправильный — пропускаем
        
        await conn.commit()

async def delete_old_appointments():
    current_year = datetime.now().year
    today = datetime.now().date()
    
    async with async_engine.connect() as conn:
        result = await conn.execute(select(appointments_table))
        appointments = result.fetchall()
        
        for app in appointments:
            try:
                app_date = datetime.strptime(f"{app.date}.{current_year}", "%d.%m.%Y").date()
                if app_date < today:
                    await conn.execute(delete(appointments_table).where(
                        appointments_table.c.id == app.id
                    ))
            except ValueError:
                pass
        
        await conn.commit()