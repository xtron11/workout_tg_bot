from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from core import insert_user, insert_appointment, get_user, delete_slot_from_db, delete_appointment_by_id, get_user_appointments,add_available_slot, get_appointment_by_id, get_appointment_by_day
from keyboards import get_days_keyboard, get_time_keyboard, get_main_menu, get_cancel_kb, get_appointments_kb
from config import settings
import re

user_router = Router()

class Form(StatesGroup):
    name = State()
    age = State()
    main_menu = State() # Новое состояние выбора
    day = State()
    time = State()
    waiting_for_homework = State() # Состояние для приема ДЗ

def extract_number(text):
    match = re.search(r'\b(\d+)\b', text)
    return int(match.group(1)) if match else None

async def show_main_menu(message: types.Message, state: FSMContext, tg_id: int):
    appointment = await get_user_appointments(tg_id)
    await message.answer(
        "Что хочешь сделать?",
        reply_markup=get_main_menu(has_appointment=bool(appointment))
    )
    await state.set_state(Form.main_menu)

# --- Команды ---
@user_router.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Все состояния сброшены. Попробуй теперь /start_questionnaire")

@user_router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    user = await get_user(tg_id=message.from_user.id)
    
    if user:
        # Уже зарегистрирован — сразу в меню
        await message.answer(
            f"С возвращением, {message.from_user.first_name}! Что хочешь сделать?",
            reply_markup=get_main_menu()
        )
        await state.set_state(Form.main_menu)
    else:
        # Новый пользователь — на регистрацию
        await message.answer(
            f"Привет, {message.from_user.first_name}! "
            "Для записи на тренировку начни опрос командой /start_questionnaire"
        )

@user_router.message(Command('start_questionnaire'))
async def start_reg(message: types.Message, state: FSMContext):
    await message.answer('Привет! Как тебя зовут?')
    await state.set_state(Form.name)


@user_router.message(Form.name)
async def capture_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer('Супер! А сколько тебе полных лет?')
    await state.set_state(Form.age)

@user_router.message(Form.age)
async def capture_age(message: types.Message, state: FSMContext):
    age = extract_number(message.text)
    if not age or not (1 <= age <= 100):
        await message.reply('Введите корректный возраст.')
        return
    
    data = await state.get_data()
    await insert_user(tg_id=message.from_user.id, username=data.get("name"), age=age)
    
    # Показываем главное меню
    await message.answer(
        "Регистрация прошла успешно! Что вы хотите сделать?",
        reply_markup=get_main_menu()
    )
    await state.set_state(Form.main_menu)
    
@user_router.message(Form.main_menu, F.text == "Записаться на тренировку")
async def start_booking(message: types.Message, state: FSMContext):
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
    await show_main_menu(message, state, message.from_user.id)

@user_router.message(Form.main_menu, F.text == "Перезаписаться на другое время")
async def rebooking(message: types.Message):
    appointments = await get_user_appointments(tg_id=message.from_user.id)
    
    if not appointments:
        await message.answer("У вас нет активных записей.")
        return
    
    reply_markup = await get_appointments_kb(appointments, action="rebook")
    await message.answer("Какую запись изменить?", reply_markup=reply_markup)

# 2. В функции capture_day
@user_router.callback_query(Form.day, F.data.startswith("day_"))
async def capture_day(callback: types.CallbackQuery, state: FSMContext):
    selected_day = callback.data.split("_")[1]
    
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

    user = await get_user(tg_id=callback.from_user.id)
    user_name = user.username if user else callback.from_user.first_name

    # 1. Сохраняем в базу (как ты уже делал)
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
    
    await show_main_menu(callback.message, state, callback.from_user.id)
    await callback.answer()