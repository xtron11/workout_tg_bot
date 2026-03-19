from aiogram.types import InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from core import get_unique_days_from_db, get_times_for_day_from_db

def get_main_menu(has_appointment: bool = False):
    kb = [
        [KeyboardButton(text="Записаться на тренировку")],
    ]
    if has_appointment:
        kb.insert(1, [KeyboardButton(text="Перезаписаться на другое время")])
        kb.insert(2, [KeyboardButton(text="Моя запись")])
        kb.insert(3, [KeyboardButton(text="Отменить запись")])
    
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_admin_menu():
    kb = [
        [KeyboardButton(text="➕ Добавить запись")],
        [KeyboardButton(text="Посмотреть запись / 🗑 Удалить запись")],
        [KeyboardButton(text="👥 Пользователи")],
    ]
    
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_approve_kb(tg_id: int, first_name: str, last_name: str):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="✅ Одобрить",
        callback_data=f"approve_{tg_id}:{first_name}:{last_name}"
    ))
    builder.adjust(1)
    return builder.as_markup()

def get_cancel_kb():
    kb = [[KeyboardButton(text="❌ Отмена")]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

async def get_days_keyboard():
    builder = InlineKeyboardBuilder()
    # Получаем список дней напрямую из базы
    days = await get_unique_days_from_db()
    
    if not days:
        return None # Если админ ничего не добавил, кнопок не будет

    for day in days:
        builder.add(InlineKeyboardButton(text=day, callback_data=f"day_{day}"))
    builder.adjust(2)
    return builder.as_markup()

async def get_time_keyboard(day: str):
    builder = InlineKeyboardBuilder()
    # Получаем время только для этого дня из базы
    times = await get_times_for_day_from_db(day)
    
    times = sorted(times) # Сортируем время

    for t in times:
        builder.add(InlineKeyboardButton(text=t, callback_data=f"time_{t}"))
    builder.adjust(3)
    return builder.as_markup()

async def get_appointments_kb(appointments: list, action: str):
    builder = InlineKeyboardBuilder()
    for app in appointments:
        builder.add(InlineKeyboardButton(
            text=f"{app.date} в {app.time}",
            callback_data=f"{action}_{app.id}"  # action = "cancel" или "rebook"
        ))
    builder.adjust(1)
    return builder.as_markup()

def get_admin_time_kb(selected_times: list):
    builder = InlineKeyboardBuilder()
    hours = ["12:00", "13:00", "14:00", "15:00", "16:00", "17:00"]
    
    for h in hours:
        # Если час уже в списке выбранных, добавляем галочку
        text = f"✅ {h}" if h in selected_times else h
        builder.add(InlineKeyboardButton(text=text, callback_data=f"admin_time_{h}"))
    
    builder.add(InlineKeyboardButton(text="➕ Свое время", callback_data="admin_custom_time"))
    builder.add(InlineKeyboardButton(text="💾 Сохранить", callback_data="admin_save_slots"))
    
    builder.adjust(2)
    return builder.as_markup()

async def get_admin_times_kb(slots: list):
    builder = InlineKeyboardBuilder()
    for slot in slots:
        if slot.status == "free":
            builder.add(InlineKeyboardButton(
                text=f"🟢 {slot.time} — свободно",
                callback_data=f"admin_delete_slot_{slot.id}"  # ничего не делаем при нажатии
            ))
        else:
            builder.add(InlineKeyboardButton(
                text=f"❌ {slot.time} — {slot.username}",
                callback_data=f"admin_select_{slot.id}"
            ))
            
    builder.add(InlineKeyboardButton(
        text="◀️ Назад",
        callback_data="admin_back_to_days"
        ))
    
    builder.adjust(1)
    return builder.as_markup()

async def get_admin_all_days_kb(days: list):
    builder = InlineKeyboardBuilder()
    seen = set()  # чтобы не было дублей
    for row in days:
        day = row[0]  # days это список кортежей ("21.03",)
        if day not in seen:
            seen.add(day)
            builder.add(InlineKeyboardButton(
                text=f"📅 {day}",
                callback_data=f"admin_day_{day}"
            ))
            
    builder.add(InlineKeyboardButton(
        text="🏠 Главное меню",
        callback_data="admin_to_main"
        ))
    
    builder.adjust(1)
    return builder.as_markup()

def get_admin_action_kb(appointment_id: int):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🗑 Удалить весь слот", callback_data=f"admin_delete_full_{appointment_id}"))
    builder.add(InlineKeyboardButton(text="👤 Убрать запись пользователя", callback_data=f"admin_delete_user_{appointment_id}"))
    builder.add(InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back_to_days"))
    builder.adjust(1)
    return builder.as_markup()

# Кнопки удаления пользователя из БД
async def get_users_kb(users: list):
    builder = InlineKeyboardBuilder()
    for user in users:
        builder.add(InlineKeyboardButton(
            text=f"❌ {user.first_name} {user.last_name}",
            callback_data=f"delete_user_{user.tg_id}"
        ))
    builder.adjust(1)
    return builder.as_markup()