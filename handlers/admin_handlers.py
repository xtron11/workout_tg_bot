from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from core import add_available_slot, delete_appointment_by_id, get_appointment_by_id, get_slots_and_appointments_by_day, get_all_days, delete_slot_by_id, get_all_users, get_users_for_notification, insert_user, delete_user
from keyboards import get_admin_time_kb, get_admin_times_kb, get_admin_all_days_kb, get_admin_action_kb, get_admin_menu, get_users_kb
from config import settings
import re

admin_router = Router()

class AdminForm(StatesGroup):
    admin_main = State()
    waiting_for_day = State()
    waiting_for_time = State()
    waiting_for_custom_time = State()
    delete_day = State()
    delete_time = State()

# Делаем проверку для ввода даты, чтобы формат был только к примеру 20.01, 01.07
def validate_date(text):
    match = re.match(r'^(\d{2})\.(\d{2})$', text)
    if not match:
        return False
    day, month = int(match.group(1)), int(match.group(2))
    return 1 <= day <= 31 and 1 <= month <= 12

def validate_time(text):
    match = re.match(r'^(\d{2}):(\d{2})$', text)
    if not match:
        return False
    hour, minute = int(match.group(1)), int(match.group(2))
    return 0 <= hour <= 23 and 0 <= minute <= 59

@admin_router.message(Command("start"), F.from_user.id == settings.ADMIN_ID)
async def admin_start(message: types.Message, state: FSMContext):
    await message.answer(
        f"Привет, {message.from_user.first_name}! Панель админа:",
        reply_markup=get_admin_menu()
    )
    await state.set_state(AdminForm.admin_main)

# Основное меню
@admin_router.callback_query(F.data == "admin_to_main")
async def admin_to_main(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer(
        "Панель админа:",
        reply_markup=get_admin_menu()
    )
    await state.set_state(AdminForm.admin_main)
    await callback.answer()

# Подтверждаем новых пользователей
@admin_router.callback_query(F.data.startswith("approve_"))
async def approve(callback: types.CallbackQuery):
    parts = callback.data.split("_", 1)[1]
    tg_id, first_name, last_name = parts.split(":")

    await insert_user(int(tg_id), first_name, last_name)
    await callback.bot.send_message(
        chat_id=int(tg_id),
        text="✅ Ваша регистрация одобрена! Напишите /start чтобы начать."
    )
    await callback.message.edit_text("✅ Одобрен")
    await callback.answer()


@admin_router.message(AdminForm.admin_main,  F.text == "➕ Добавить запись")
async def admin_add_start(message: types.Message, state: FSMContext):
    await message.answer("На какое число (день) создаем записи? (например: 20.03)")
    await state.set_state(AdminForm.waiting_for_day)


@admin_router.message(AdminForm.waiting_for_day)
async def admin_get_day(message: types.Message, state: FSMContext):
    # Получаем день от админа, проверяем формат и показываем выбор времени
    if not validate_date(message.text):
        await message.answer("Введите дату в правильном формате (например: 20.03, 09.04)")
        return  # остаёмся в том же состоянии, ждём правильный ввод
    
    await state.update_data(admin_day=message.text, selected_times=[])
    await message.answer(
        f"Выбрано: {message.text}\nОтметьте нужное время:",
        reply_markup=get_admin_time_kb([])
    )
    await state.set_state(AdminForm.waiting_for_time)
        

# Обработка кликов по времени (Чекбоксы)
@admin_router.callback_query(AdminForm.waiting_for_time, F.data.startswith("admin_time_"))
async def admin_toggle_time(callback: types.CallbackQuery, state: FSMContext):
    clicked_time = callback.data.split("_")[2]
    data = await state.get_data()
    selected = data.get("selected_times", [])

    if clicked_time in selected:
        selected.remove(clicked_time) # Убираем галочку
    else:
        selected.append(clicked_time) # Ставим галочку

    await state.update_data(selected_times=selected)
    
    # Обновляем сообщение с новой клавиатурой
    await callback.message.edit_reply_markup(reply_markup=get_admin_time_kb(selected))
    await callback.answer()

# Сохранение в базу
@admin_router.callback_query(AdminForm.waiting_for_time, F.data == "admin_save_slots")
async def admin_save(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    day = data.get("admin_day")
    times = data.get("selected_times")

    if not times:
        await callback.answer("Выберите хотя бы одно время!", show_alert=True)
        return

    for t in times:
        await add_available_slot(day, t)

    users = await get_users_for_notification()

    # Уведомляем пользователя о новой записи
    admin_text = (f"🔔 Появилась новая запись!\n"
                  f"📅 Дата: {day}\n"
                  f"⏰ Время: {', '.join(times)}\n"  # все времена
                  f"Запишись через /start")
    
    # Отправляем каждому пользователю из бд, уведомление
    for user in users:
        await callback.bot.send_message(chat_id=user, text=admin_text)
    
    await callback.message.edit_text(f"✅ Готово! Добавлены слоты на {day}: {', '.join(times)}\n Пользователи уведомлены")
    await state.set_state(AdminForm.admin_main)

@admin_router.callback_query(AdminForm.waiting_for_time, F.data == "admin_custom_time")
async def admin_custom_ask(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите время вручную (например, 18:30):")
    await state.set_state(AdminForm.waiting_for_custom_time)
    await callback.answer()

@admin_router.message(AdminForm.waiting_for_custom_time)
async def admin_custom_ask_time(message: types.Message, state: FSMContext):
    if not validate_time(message.text):
        await message.answer("Введите время в правильном формате (например: 12:30, 09:10)")
        return
    
    # Достаём текущий список выбранных времён
    data = await state.get_data()
    selected = data.get("selected_times", [])
    
    # Добавляем новое время
    selected.append(message.text)
    await state.update_data(selected_times=selected)
    
    # Возвращаемся к выбору времени
    await message.answer(
        f"✅ Время {message.text} добавлено!",
        reply_markup=get_admin_time_kb(selected)
    )
    await state.set_state(AdminForm.waiting_for_time)

# Общая функция — показывает дни
async def show_days(target, state: FSMContext):
    days = await get_all_days()
    if not days:
        await target.answer("Записей нет.")
        return
    await target.answer(
        "Выберите день:",
        reply_markup=await get_admin_all_days_kb(days)
    )
    await state.set_state(AdminForm.delete_day)

# Удалить
@admin_router.message(AdminForm.admin_main,  F.text == "Посмотреть запись / 🗑 Удалить запись")
async def admin_delete(message: types.Message, state: FSMContext):
    await show_days(message, state)

# Кнопка назад
@admin_router.callback_query(AdminForm.delete_time, F.data == "admin_back_to_days")
async def admin_back(callback: types.CallbackQuery, state: FSMContext):
    # Возвращаемся к списку дней
    days = await get_all_days()
    await callback.message.edit_text(
    "Выберите день:",
    reply_markup=await get_admin_all_days_kb(days)
    )
    await state.set_state(AdminForm.delete_day)
    await callback.answer()

# Шаг 2 — нажали на день, показываем слоты и записи
@admin_router.callback_query(AdminForm.delete_day, F.data.startswith("admin_day_"))
async def admin_show_times(callback: types.CallbackQuery, state: FSMContext):
    # Показываем все слоты на выбранный день — свободные и занятые
    selected_day = callback.data.split("_")[2]
    
    slots = await get_slots_and_appointments_by_day(selected_day)  # передаём день!
    
    if not slots:
        await callback.message.edit_text("На этот день ничего нет.")
        await callback.answer()
        return
    
    await callback.message.edit_text(
        f"Записи на {selected_day}:",
        reply_markup=await get_admin_times_kb(slots)
    )
    await callback.answer()
    await state.set_state(AdminForm.delete_time)

# Делаем выбор действий после выбора записи
@admin_router.callback_query(AdminForm.delete_time, F.data.startswith("admin_select_"))
async def admin_select(callback: types.CallbackQuery, state: FSMContext):
    appointment_id = int(callback.data.split("_")[2])

    await callback.message.edit_text(
        "Выберите действие:",
        reply_markup=get_admin_action_kb(appointment_id)
    )
    await callback.answer()

# Удаляем свободную запись
@admin_router.callback_query(AdminForm.delete_time, F.data.startswith("admin_delete_slot_"))
async def admin_delete_slot(callback, state):
    slot_id = int(callback.data.split("_")[3])
    await delete_slot_by_id(slot_id)  # из available_slots
    
    days = await get_all_days()
    if days:
        await callback.message.edit_text(
            "✅ Слот удалён. Выберите день:",
            reply_markup=await get_admin_all_days_kb(days)
        )
        await state.set_state(AdminForm.delete_day)
    else:
        await callback.message.edit_text("✅ Слот удалён. Записей больше нет.")
        await state.clear()
    
    await callback.answer()

# Удаляем запись полностью
@admin_router.callback_query(AdminForm.delete_time, F.data.startswith("admin_delete_full_"))
async def admin_delete_full(callback, state):
    appointment_id = int(callback.data.split("_")[3])
    
    # Сначала получаем — потом удаляем
    appointment = await get_appointment_by_id(appointment_id)
    await delete_appointment_by_id(appointment_id)

    if appointment:
        await callback.bot.send_message(
            chat_id=appointment.user_tg_id,
            text=f"❌ Ваша запись на {appointment.date} в {appointment.time} была отменена тренером."
        )

    days = await get_all_days()
    if days:
        await callback.message.edit_text(
            "✅ Слот удалён. Выберите день:",
            reply_markup=await get_admin_all_days_kb(days)
        )
        await state.set_state(AdminForm.delete_day)
    else:
        await callback.message.edit_text("✅ Слот удалён. Записей больше нет.")
        await state.clear()
    
    await callback.answer()

# Удаляем только запись пользователя
@admin_router.callback_query(AdminForm.delete_time, F.data.startswith("admin_delete_user_"))
async def admin_delete_user_(callback: types.CallbackQuery, state: FSMContext):
    appointment_id = int(callback.data.split("_")[3])
    appointment = await get_appointment_by_id(appointment_id)

    if appointment:
        await delete_appointment_by_id(appointment_id)
        await add_available_slot(appointment.date, appointment.time)
        await callback.bot.send_message(
            chat_id=appointment.user_tg_id,
            text=f"❌ Ваша запись на {appointment.date} в {appointment.time} была отменена тренером."
        )
    else:
        await callback.message.edit_text("Запись не найдена.")
    
    await callback.answer()
    days = await get_all_days()
    if days:
        await callback.message.edit_text(
            "✅ Запись удалена. Выберите день:",
            reply_markup=await get_admin_all_days_kb(days)
        )
        await state.set_state(AdminForm.delete_day)
    else:
        await state.clear()

@admin_router.message(AdminForm.admin_main, F.text == "👥 Пользователи")
async def admin_users(message: types.Message):
    users = await get_all_users()
    if users:
        text = "👥 Все пользователи:\n"
        for user in users:
            text += f"\n👤 {user.first_name} {user.last_name} | tg_id:{user.tg_id}\n📅 Дата регистрации: {user.created_on}\n"
        await message.answer(text, reply_markup=await get_users_kb(users))
    else:
        await message.answer("Нет пользователей")

@admin_router.callback_query(F.data.startswith("delete_user_"))
async def delete_user_(callback: types.CallbackQuery):
    tg_id = int(callback.data.split("_")[2])
    await delete_user(tg_id)  # просто удаляем, без проверки

    await callback.bot.send_message(
        chat_id=tg_id,
        text="❌ Ваш аккаунт был удалён тренером. Напишите /start чтобы подать заявку снова."
    )
    # Показываем обновлённый список
    users = await get_all_users()
    if users:
        text = "👥 Все пользователи:\n"
        for user in users:
            text += f"\n👤 {user.first_name} {user.last_name} | tg_id:{user.tg_id}\n"
        await callback.message.edit_text(text, reply_markup=await get_users_kb(users))
    else:
        await callback.message.edit_text("Нет пользователей")
    
    await callback.message.answer("✅ Пользователь удалён")
    