from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from core import insert_appointment, get_user, delete_slot_from_db, delete_appointment_by_id, get_user_appointments,add_available_slot, get_appointment_by_id, get_appointment_by_day
from keyboards import get_days_keyboard, get_time_keyboard, get_main_menu, get_cancel_kb, get_appointments_kb, get_approve_kb
from config import settings
import re

user_router = Router()

class Form(StatesGroup):
    main_menu = State()
    day = State()
    time = State()


# Основное меню
async def show_main_menu(message: types.Message, state: FSMContext, tg_id: int):
    user = await get_user(tg_id)
    if not user:
        await state.clear()
        await message.answer("У вас нет доступа. Напишите /start.")
        return

    appointment = await get_user_appointments(tg_id)
    await message.answer(
        "Что хочешь сделать?",
        reply_markup=get_main_menu(has_appointment=bool(appointment))
    )
    await state.set_state(Form.main_menu)

# --- Команды ---
@user_router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    user = await get_user(tg_id=message.from_user.id)
    
    if user:
        await show_main_menu(message, state, message.from_user.id)
    else:
        await state.clear() # Сбрасываем состояние чтобы после удаления пользователя у него не было кнопок
        await message.answer(
        f"Привет, {message.from_user.first_name}! "
        "Ваш запрос на регистрацию отправлен, как только тренер одобрит вы получите уведомление."
        )
        # Уведомляем тренера с кнопкой одобрения
        await message.bot.send_message(
            chat_id=settings.ADMIN_ID,
            text=f"🔔 Новый пользователь хочет записаться!\n"
                f"👤 Имя: {message.from_user.first_name}\n"
                f"🔗 TG: @{message.from_user.username}\n"
                f"🆔 ID: {message.from_user.id}",
            reply_markup=get_approve_kb(
                tg_id=message.from_user.id,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name or ""  # last_name может быть None
            )
        )

@user_router.message(Form.main_menu, F.text == "Записаться на тренировку")
async def start_booking(message: types.Message, state: FSMContext):
    user = await get_user(tg_id=message.from_user.id)
    if not user:
        await state.clear()
        await message.answer("У вас нет доступа. Напишите /start.")
        return
    
    reply_markup = await get_days_keyboard()
    
    if reply_markup is None:
        await message.answer("Извините, свободных дней для записи пока нет.")
        return

    await message.answer(
        "Выберите день для тренировки:",
        reply_markup=get_cancel_kb()
    )
    await message.answer("👇", reply_markup=reply_markup)
    await state.set_state(Form.day)

@user_router.callback_query(Form.main_menu, F.data.startswith("rebook_"))
async def confirm_rebook(callback: types.CallbackQuery, state: FSMContext):
    appointment_id = int(callback.data.split("_")[1])
    appointment = await get_appointment_by_id(appointment_id)

    # Удаляем старую запись и возвращаем слот, затем показываем выбор дня
    if appointment:
        # Сохраняем id записи которую меняем
        await state.update_data(rebook_appointment_id=appointment_id)
        await delete_appointment_by_id(appointment_id)
        await add_available_slot(appointment.date, appointment.time)
    
    reply_markup = await get_days_keyboard()
    if reply_markup is None:
        await callback.message.edit_text("Свободных дней пока нет.")
        await callback.answer()
        return

    await callback.message.edit_text("Выберите новый день:")
    await callback.message.answer("👇", reply_markup=reply_markup)
    await state.set_state(Form.day)
    await callback.answer()

@user_router.message(F.text == "❌ Отмена")
async def cmd_cancel_button(message: types.Message, state: FSMContext):
    await state.clear()
    await show_main_menu(message, state, message.from_user.id) # Показываем main_menu при нажатии на Отмена

@user_router.message(Form.main_menu, F.text == "Перезаписаться на другое время")
async def rebooking(message: types.Message):
    appointments = await get_user_appointments(tg_id=message.from_user.id)
    
    if not appointments:
        await message.answer("У вас нет активных записей.")
        return
    
    reply_markup = await get_appointments_kb(appointments, action="rebook")
    await message.answer("Какую запись изменить?", reply_markup=reply_markup)

@user_router.callback_query(Form.day, F.data.startswith("day_"))
async def capture_day(callback: types.CallbackQuery, state: FSMContext):
    selected_day = callback.data.split("_")[1] # Парсим чтобы получить число дня
    
    # Проверяем не записан ли уже пользователь на этот день
    existing = await get_appointment_by_day(
        tg_id=callback.from_user.id, 
        day=selected_day
    )
    if existing:
        await callback.answer(
            f"Вы уже записаны на {selected_day}!\nИспользуйте кнопку 'Перезаписаться'.",
            show_alert=True
        )
        return
    
    await state.update_data(day=selected_day)
    reply_markup = await get_time_keyboard(selected_day)
    
    if not reply_markup:
        await callback.answer("Все слоты на этот день уже заняты!", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"Вы выбрали: {selected_day}. Теперь выберите время:", 
        reply_markup=reply_markup
    )
    await state.set_state(Form.time)
    await callback.answer()

@user_router.callback_query(Form.time, F.data.startswith("time_"))
async def capture_time(callback: types.CallbackQuery, state: FSMContext):
    selected_time = callback.data.split("_")[1]
    data = await state.get_data()
    selected_day = data.get('day')
    is_rebook = data.get("rebook_appointment_id") is not None

    user = await get_user(tg_id=callback.from_user.id)
    user_name = user.first_name if user else callback.from_user.first_name # Берём имя из БД, если пользователь не найден то берём из Телеграма

    # 1. Сохраняем в базу
    await insert_appointment(
        user_tg_id=callback.from_user.id,
        username=user_name,
        day=selected_day,
        time=selected_time
    )

    # 2. Формируем текст подтверждения для пользователя
    res_text = f"✅ Запись подтверждена!\nДень: {selected_day}\nВремя: {selected_time}"
    await callback.message.edit_text(res_text)

    await delete_slot_from_db(selected_day, selected_time)

    # 3. УВЕДОМЛЕНИЕ АДМИНА
    if is_rebook:
        admin_text = (f"🔔 Пользователь перезаписался!\n"
              f"👤 Имя: {user_name}\n"
              f"📅 Дата: {selected_day}\n"
              f"⏰ Время: {selected_time}\n"
              f"🔗 TG: @{callback.from_user.username}")
    else:
        admin_text = (f"🔔 Новая запись!\n"
                    f"👤 Имя: {user_name}\n"
                    f"📅 Дата: {selected_day}\n"
                    f"⏰ Время: {selected_time}\n"
                    f"🔗 TG: @{callback.from_user.username}")
    
    # Отправляем сообщение админу напрямую через объект bot
    await callback.bot.send_message(chat_id=settings.ADMIN_ID, text=admin_text)

    await state.clear()
    # Показываем меню с кнопкой перезаписи
    await show_main_menu(callback.message, state, callback.from_user.id)
    await callback.answer()

@user_router.message(Form.main_menu, F.text == "Моя запись")
async def my_appointments(message: types.Message):
    appointments = await get_user_appointments(tg_id=message.from_user.id)
    
    if appointments:
        text = "📅 Ваши записи:\n\n"
        for app in appointments:
            text += f"• {app.date} в {app.time}\n"
        await message.answer(text)
    else:
        await message.answer("У вас нет активных записей.")

# Отменить запись — показываем список
@user_router.message(Form.main_menu, F.text == "Отменить запись")
async def cancel_appointment(message: types.Message):
    appointments = await get_user_appointments(tg_id=message.from_user.id)
    
    if not appointments:
        await message.answer("У вас нет активных записей.")
        return
    
    reply_markup = await get_appointments_kb(appointments, action="cancel")
    await message.answer("Какую запись отменить?", reply_markup=reply_markup)

# Отменить запись — обработка нажатия на кнопку
@user_router.callback_query(Form.main_menu, F.data.startswith("cancel_"))
async def confirm_cancel(callback: types.CallbackQuery, state: FSMContext):
    appointment_id = int(callback.data.split("_")[1])
    appointment = await get_appointment_by_id(appointment_id)
    
    if appointment:
        await delete_appointment_by_id(appointment_id)
        await add_available_slot(appointment.date, appointment.time)
        await callback.message.edit_text("✅ Запись отменена.")
        await callback.bot.send_message(
            chat_id=settings.ADMIN_ID,
            text=f"🔔 Пользователь @{callback.from_user.username} отменил запись на {appointment.date} в {appointment.time}"
        )
    
    await show_main_menu(callback.message, state, callback.from_user.id)
    await callback.answer()