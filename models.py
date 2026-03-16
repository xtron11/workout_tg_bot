from sqlalchemy import Table, Column, Integer, String, MetaData, DateTime, Time, BigInteger, ForeignKey, Boolean
from datetime import datetime

metadata_obj = MetaData()

workers_table = Table(
    "users",
    metadata_obj,
    Column("id", Integer, primary_key=True),
    Column("tg_id", BigInteger, unique=True),
    Column("username", String),
    Column("age", Integer),
    Column("created_on", DateTime(), default=datetime.utcnow) # Используем utcnow
)

appointments_table = Table(
    "appointments",
    metadata_obj,
    Column("id", Integer, primary_key=True), # У каждой записи свой уникальный ID
    Column("user_tg_id", BigInteger, ForeignKey('users.tg_id')), # Привязываемся к tg_id
    Column("username", String),
    Column("date", String),
    Column("time", String),
    Column("created_on", DateTime(), default=datetime.utcnow) # Используем utcnow
)

available_slots_table = Table(
    "available_slots",
    metadata_obj,
    Column("id", Integer, primary_key=True),
    Column("day", String),  # Например, "Понедельник" или "20.05"
    Column("time", String), # Например, "14:00"
    Column("is_taken", Boolean, default=False) # Занято ли это место
)