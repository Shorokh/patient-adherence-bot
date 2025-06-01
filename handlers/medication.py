# Файл: handlers/medication.py

from aiogram import types, Dispatcher
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from utils.db import SessionLocal
from models.medication import Medication
from models.reminder import Reminder
from models.user import User
from utils.helpers import parse_time_list, calculate_next_due_for_timezone

from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove
)


# --------------- FSM-состояния ---------------
class MedicationStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_dosage = State()
    waiting_for_type = State()
    waiting_for_times = State()
    waiting_for_conditions = State()
    waiting_for_skip = State()


# --------------- Клавиатуры ---------------
def cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Отмена")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def type_inline_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Регулярный", callback_data="medtype_regular"),
            InlineKeyboardButton(text="Ситуативный", callback_data="medtype_situational"),
        ]
    ])


def skip_inline_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Удвоить", callback_data="skp_double"),
            InlineKeyboardButton(text="Пропустить", callback_data="skp_skip"),
            InlineKeyboardButton(text="Без напоминаний", callback_data="skp_none"),
        ]
    ])


# --------------- Хэндлер отмены ---------------
async def cancel_medication(message: types.Message, state: FSMContext):
    curr_state = await state.get_state()
    if curr_state is None:
        await message.answer("Нечего отменять.")
        return

    await state.clear()
    await message.answer(
        "Добавление препарата отменено. Вы возвращены в главное меню.",
        reply_markup=ReplyKeyboardRemove()
    )
    from handlers.menu import main_menu_keyboard

    session = SessionLocal()
    user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
    session.close()
    if user:
        kb = main_menu_keyboard(user)
        await message.answer("Главное меню:", reply_markup=kb)


# --------------- Основные хэндлеры FSM ---------------
async def cmd_add_med(message: types.Message, state: FSMContext):
    await message.answer("Введите название препарата:", reply_markup=cancel_keyboard())
    await state.set_state(MedicationStates.waiting_for_name)


async def process_name(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if text == "Отмена":
        return await cancel_medication(message, state)

    await state.update_data(name=text)
    await message.answer("Введите дозировку (например, 500 мг):", reply_markup=cancel_keyboard())
    await state.set_state(MedicationStates.waiting_for_dosage)


async def process_dosage(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if text == "Отмена":
        return await cancel_medication(message, state)

    await state.update_data(dosage=text)

    # Удаляем Reply-клавиатуру, показываем Inline-кнопки для выбора типа
    await message.answer(
        "Выберите тип приёма:",
        reply_markup=type_inline_kb()
    )
    await state.set_state(MedicationStates.waiting_for_type)


# Обработка текстового ввода «Регулярный»/«Ситуативный» вместо кнопки
async def process_type_text(message: types.Message, state: FSMContext):
    text = message.text.strip().lower()
    if text == "отмена":
        return await cancel_medication(message, state)

    if text not in ["регулярный", "ситуативный"]:
        await message.answer(
            "Пожалуйста, выберите «Регулярный» или «Ситуативный» кнопкой, либо нажмите «Отмена».",
            reply_markup=type_inline_kb()
        )
        return

    intake_type = "regular" if text == "регулярный" else "situational"
    await state.update_data(intake_type=intake_type)

    # Удаляем сообщение с кнопками
    await message.delete()

    if intake_type == "regular":
        await message.answer(
            "Введите время приёма в формате чч:мм (например, 08:30) или несколько через запятую:",
            reply_markup=cancel_keyboard()
        )
        await state.set_state(MedicationStates.waiting_for_times)
    else:
        await state.update_data(times=[])
        await message.answer(
            "Введите условия приёма (через запятую) или «нет»:",
            reply_markup=cancel_keyboard()
        )
        await state.set_state(MedicationStates.waiting_for_conditions)


async def process_type(callback: types.CallbackQuery, state: FSMContext):
    intake_type = "regular" if callback.data.endswith("_regular") else "situational"
    await state.update_data(intake_type=intake_type)

    # Удаляем сообщение с Inline-кнопками
    await callback.message.delete()

    if intake_type == "regular":
        await callback.message.answer(
            "Введите время приёма в формате чч:мм (например, 08:30) или несколько через запятую:",
            reply_markup=cancel_keyboard()
        )
        await state.set_state(MedicationStates.waiting_for_times)
    else:
        await state.update_data(times=[])
        await callback.message.answer(
            "Введите условия приёма (через запятую) или «нет»:",
            reply_markup=cancel_keyboard()
        )
        await state.set_state(MedicationStates.waiting_for_conditions)

    await callback.answer()


async def process_times(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if text == "Отмена":
        return await cancel_medication(message, state)

    times = parse_time_list(text)
    if not times:
        await message.answer(
            "Неверный формат времени. Повторите в формате чч:мм (например, 08:30) или нажмите «Отмена».",
            reply_markup=cancel_keyboard()
        )
        return

    await state.update_data(times=times)
    await message.answer("Введите условия приёма (через запятую) или «нет»:", reply_markup=cancel_keyboard())
    await state.set_state(MedicationStates.waiting_for_conditions)


async def process_conditions(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if text == "Отмена":
        return await cancel_medication(message, state)

    cond_text = text.lower()
    conditions = [] if cond_text == "нет" else [c.strip() for c in text.split(",")]
    await state.update_data(conditions=conditions)

    data = await state.get_data()
    if data["intake_type"] == "regular":
        await message.answer(
            "Выберите поведение при пропуске:",
            reply_markup=skip_inline_kb()
        )
        await state.set_state(MedicationStates.waiting_for_skip)
    else:
        # Ситуативный: сразу сохраняем
        await save_medication(callback_or_message=message, state=state)


async def process_skip(callback: types.CallbackQuery, state: FSMContext):
    skip_mode = callback.data.split("_")[1]  # "double", "skip" или "none"
    await state.update_data(skip_behavior=skip_mode)
    await save_medication(callback_or_message=callback, state=state)
    await callback.answer()


async def save_medication(callback_or_message, state: FSMContext):
    data = await state.get_data()
    session = SessionLocal()

    med = Medication(
        user_id=callback_or_message.from_user.id,
        name=data["name"],
        dosage=data["dosage"],
        intake_type=data["intake_type"],
        time_list=data.get("times", []),
        conditions=data.get("conditions", []),
        skip_behavior=data.get("skip_behavior", ""),
        is_active=True
    )
    session.add(med)
    session.commit()
    session.refresh(med)

    if med.intake_type == "regular" and med.time_list:
        user = session.query(User).filter(User.telegram_id == callback_or_message.from_user.id).first()
        tz = user.timezone or "+00:00"
        next_due_utc = calculate_next_due_for_timezone(med.time_list, tz)
        rem = Reminder(
            medication_id=med.id,
            next_due=next_due_utc,
            retry_count=0,
            is_active=True
        )
        session.add(rem)
        session.commit()

    session.close()

    from handlers.menu import main_menu_keyboard

    # Определяем, как отвечать: через message или callback.message
    if isinstance(callback_or_message, types.CallbackQuery):
        await callback_or_message.message.answer("✅ Препарат добавлен успешно!", reply_markup=ReplyKeyboardRemove())
        chat = callback_or_message.message
    else:
        await callback_or_message.answer("✅ Препарат добавлен успешно!", reply_markup=ReplyKeyboardRemove())
        chat = callback_or_message

    # Показываем главное меню с кнопками
    session = SessionLocal()
    user = session.query(User).filter(User.telegram_id == callback_or_message.from_user.id).first()
    session.close()
    if user:
        kb = main_menu_keyboard(user)
        await chat.answer("Главное меню:", reply_markup=kb)

    await state.clear()


# --------------- Регистрация хэндлеров ---------------
def register_handlers(dp: Dispatcher):
    # Запуск добавления препарата
    dp.message.register(cmd_add_med, lambda m: m.text == "➕ Добавить препарат")

    # Обработка «Отмена» во всех состояниях MedicationStates
    dp.message.register(cancel_medication, StateFilter(MedicationStates), lambda m: m.text == "Отмена")

    # Обработка ввода названия
    dp.message.register(
        process_name,
        StateFilter(MedicationStates.waiting_for_name)
    )

    # Обработка ввода дозировки
    dp.message.register(
        process_dosage,
        StateFilter(MedicationStates.waiting_for_dosage)
    )

    # Обработка выбора типа (Inline)
    dp.callback_query.register(
        process_type,
        lambda c: c.data and c.data.startswith("medtype_"),
        StateFilter(MedicationStates.waiting_for_type)
    )
    # Обработка текстового ввода «Регулярный»/«Ситуативный»
    dp.message.register(
        process_type_text,
        StateFilter(MedicationStates.waiting_for_type)
    )

    # Обработка ввода времени
    dp.message.register(
        process_times,
        StateFilter(MedicationStates.waiting_for_times)
    )

    # Обработка ввода условий
    dp.message.register(
        process_conditions,
        StateFilter(MedicationStates.waiting_for_conditions)
    )

    # Обработка выбора поведения skip (Inline)
    dp.callback_query.register(
        process_skip,
        lambda c: c.data and c.data.startswith("skp_"),
        StateFilter(MedicationStates.waiting_for_skip)
    )
