from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from core import add_available_slot
from keyboards import get_admin_time_kb
from config import settings

admin_router = Router()

class AdminForm(StatesGroup):
    waiting_for_day = State()
    waiting_for_time = State()


# Вместо этого пиши фильтр в каждой команде:
@admin_router.message(Command("add"), F.from_user.id == settings.ADMIN_ID)
async def admin_add_start(message: types.Message, state: FSMContext):
    await message.answer("На какое число создаем записи?")
    await state.set_state(AdminForm.waiting_for_day)

# 1. Начало: просим день
@admin_router.message(Command("add"), F.from_user.id == settings.ADMIN_ID)
async def admin_add_start(message: types.Message, state: FSMContext):
    await message.answer("На какое число (день) создаем записи? (например: 20.03)")
    await state.set_state(AdminForm.waiting_for_day)

# 2. Получаем день и показываем время
@admin_router.message(AdminForm.waiting_for_day)
async def admin_get_day(message: types.Message, state: FSMContext):
    await state.update_data(admin_day=message.text, selected_times=[])
    await message.answer(f"Выбрано: {message.text}\nОтметьте нужное время:", 
                         reply_markup=get_admin_time_kb([]))
    await state.set_state(AdminForm.waiting_for_time)

# 3. Обработка кликов по времени (Чекбоксы)
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

# 4. Сохранение в базу
@admin_router.callback_query(AdminForm.waiting_for_time, F.data == "admin_save_slots")
async def admin_save(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    day = data.get("admin_day")
    times = data.get("selected_times")

    if not times:
        await callback.answer("Выберите хотя бы одно время!", show_alert=True)
        return

    for t in times:
        await add_available_slot(day, t) # Твоя функция из core.py

    await callback.message.edit_text(f"✅ Готово! Добавлены слоты на {day}: {', '.join(times)}")
    await state.clear()

@admin_router.callback_query(AdminForm.waiting_for_time, F.data == "admin_custom_time")
async def admin_custom_ask(callback: types.CallbackQuery):
    await callback.message.answer("Введите время вручную (например, 18:30):")
    # Здесь можно добавить еще одно состояние или просто ловить следующий текст