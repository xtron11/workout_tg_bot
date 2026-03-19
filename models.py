from sqlalchemy import Table, Column, Integer, String, MetaData, DateTime, Time, BigInteger, ForeignKey, Boolean
from datetime import datetime, timezone, timedelta

metadata_obj = MetaData() # Реестр всех таблиц — нужен для create_all/drop_all

def now_utc5():
    dt = datetime.now(timezone(timedelta(hours=5))).replace(tzinfo=None)
    return dt.replace(microsecond=0)  # убираем миллисекунды

# Таблица всех наших пользователей
users_table = Table(
    "users",
    metadata_obj,
    Column("id", Integer, primary_key=True),
    Column("tg_id", BigInteger, unique=True),
    Column("first_name", String),
    Column("last_name", String), 
    Column("created_on", DateTime(), default=now_utc5)  # заменяем utcnow
)

# Таблица для записанных пользователей
appointments_table = Table(
    "appointments",
    metadata_obj,
    Column("id", Integer, primary_key=True), # У каждой записи свой уникальный ID
    Column("user_tg_id", BigInteger, ForeignKey('users.tg_id', ondelete="CASCADE")),
    Column("username", String),
    Column("date", String),
    Column("time", String),
    Column("created_on", DateTime(), default=now_utc5)  # заменяем utcnow
)

# Таблица свободных слотов которые добавляет тренер
available_slots_table = Table(
    "available_slots",
    metadata_obj,
    Column("id", Integer, primary_key=True),
    Column("day", String),  # Например, "20.05"
    Column("time", String), # Например, "14:00"
    Column("is_taken", Boolean, default=False) # Занято ли это место
)