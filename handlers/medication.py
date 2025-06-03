from aiogram import types, Dispatcher
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from utils.db import SessionLocal
from models.medication import Medication
from models.reminder import Reminder
from models.user import User
from utils.helpers import parse_time_list, calculate_next_due_for_timezone
from utils.i18n import t

from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove
)

class MedicationStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_dosage = State()
    waiting_for_type = State()
    waiting_for_times = State()
    waiting_for_conditions = State()
    waiting_for_skip = State()

def cancel_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=("Отмена" if lang == "ru" else "Cancel"))]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def type_inline_kb(lang: str) -> InlineKeyboardMarkup:
    if lang == "ru":
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Регулярный", callback_data="medtype_regular"),
                InlineKeyboardButton(text="Ситуативный", callback_data="medtype_situational")
            ]
        ])
    else:
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Regular", callback_data="medtype_regular"),
                InlineKeyboardButton(text="Situational", callback_data="medtype_situational")
            ]
        ])

def skip_inline_kb(lang: str) -> InlineKeyboardMarkup:
    if lang == "ru":
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Удвоить", callback_data="skp_double"),
                InlineKeyboardButton(text="Пропустить", callback_data="skp_skip"),
                InlineKeyboardButton(text="Без напоминаний", callback_data="skp_none")
            ]
        ])
    else:
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Double", callback_data="skp_double"),
                InlineKeyboardButton(text="Skip", callback_data="skp_skip"),
                InlineKeyboardButton(text="No reminders", callback_data="skp_none")
            ]
        ])

async def cancel_medication(message: types.Message, state: FSMContext):
    user_lang = "ru"
    session = SessionLocal()
    user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
    session.close()
    if user:
        user_lang = user.language

    curr_state = await state.get_state()
    if curr_state is None:
        await message.answer(t("nothing_to_cancel", user_lang))
        return

    await state.clear()
    await message.answer(t("cancelled", user_lang), reply_markup=ReplyKeyboardRemove())
    from handlers.menu import main_menu_keyboard

    session = SessionLocal()
    user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
    session.close()
    if user:
        kb = main_menu_keyboard(user)
        await message.answer(t("main_menu", user.language), reply_markup=kb)

async def cmd_add_med(message: types.Message, state: FSMContext):
    session = SessionLocal()
    user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
    session.close()
    lang = user.language if user else "ru"

    await message.answer(t("enter_name", lang), reply_markup=cancel_keyboard(lang))
    await state.set_state(MedicationStates.waiting_for_name)

async def process_name(message: types.Message, state: FSMContext):
    session = SessionLocal()
    user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
    session.close()
    lang = user.language if user else "ru"

    text = message.text.strip()
    if text.lower() in ["отмена", "cancel"]:
        return await cancel_medication(message, state)

    await state.update_data(name=text)
    await message.answer(t("enter_dosage", lang), reply_markup=cancel_keyboard(lang))
    await state.set_state(MedicationStates.waiting_for_dosage)

async def process_dosage(message: types.Message, state: FSMContext):
    session = SessionLocal()
    user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
    session.close()
    lang = user.language if user else "ru"

    text = message.text.strip()
    if text.lower() in ["отмена", "cancel"]:
        return await cancel_medication(message, state)

    await state.update_data(dosage=text)
    await message.answer(t("choose_type", lang), reply_markup=type_inline_kb(lang))
    await state.set_state(MedicationStates.waiting_for_type)

async def process_type_text(message: types.Message, state: FSMContext):
    session = SessionLocal()
    user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
    session.close()
    lang = user.language if user else "ru"

    text = message.text.strip().lower()
    if text in ["отмена", "cancel"]:
        return await cancel_medication(message, state)

    valid_inputs = ["регулярный", "ситуативный"] if lang == "ru" else ["regular", "situational"]
    if text not in valid_inputs:
        await message.answer(t("choose_type", lang), reply_markup=type_inline_kb(lang))
        return

    intake_type = "regular" if text in ["регулярный", "regular"] else "situational"
    await state.update_data(intake_type=intake_type)
    await message.delete()

    if intake_type == "regular":
        await message.answer(t("enter_times", lang), reply_markup=cancel_keyboard(lang))
        await state.set_state(MedicationStates.waiting_for_times)
    else:
        await state.update_data(times=[])
        await message.answer(t("enter_conditions", lang), reply_markup=cancel_keyboard(lang))
        await state.set_state(MedicationStates.waiting_for_conditions)

async def process_type(callback: types.CallbackQuery, state: FSMContext):
    session = SessionLocal()
    user = session.query(User).filter(User.telegram_id == callback.from_user.id).first()
    session.close()
    lang = user.language if user else "ru"

    intake_type = "regular" if callback.data.endswith("_regular") else "situational"
    await state.update_data(intake_type=intake_type)
    await callback.message.delete()

    if intake_type == "regular":
        await callback.message.answer(t("enter_times", lang), reply_markup=cancel_keyboard(lang))
        await state.set_state(MedicationStates.waiting_for_times)
    else:
        await state.update_data(times=[])
        await callback.message.answer(t("enter_conditions", lang), reply_markup=cancel_keyboard(lang))
        await state.set_state(MedicationStates.waiting_for_conditions)

    await callback.answer()

async def process_times(message: types.Message, state: FSMContext):
    session = SessionLocal()
    user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
    session.close()
    lang = user.language if user else "ru"

    text = message.text.strip()
    if text.lower() in ["отмена", "cancel"]:
        return await cancel_medication(message, state)

    times = parse_time_list(text)
    if not times:
        await message.answer(t("enter_times", lang), reply_markup=cancel_keyboard(lang))
        return

    await state.update_data(times=times)
    await message.answer(t("enter_conditions", lang), reply_markup=cancel_keyboard(lang))
    await state.set_state(MedicationStates.waiting_for_conditions)

async def process_conditions(message: types.Message, state: FSMContext):
    session = SessionLocal()
    user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
    session.close()
    lang = user.language if user else "ru"

    text = message.text.strip()
    if text.lower() in ["отмена", "cancel"]:
        return await cancel_medication(message, state)

    cond_text = text.lower()
    conditions = [] if cond_text in ["нет", "none"] else [c.strip() for c in text.split(",")]
    await state.update_data(conditions=conditions)

    data = await state.get_data()
    if data["intake_type"] == "regular":
        await message.answer(t("choose_skip", lang), reply_markup=skip_inline_kb(lang))
        await state.set_state(MedicationStates.waiting_for_skip)
    else:
        await save_medication(callback_or_message=message, state=state)

async def process_skip(callback: types.CallbackQuery, state: FSMContext):
    session = SessionLocal()
    user = session.query(User).filter(User.telegram_id == callback.from_user.id).first()
    session.close()
    lang = user.language if user else "ru"

    skip_mode = callback.data.split("_")[1]
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

    user_session = SessionLocal()
    user = user_session.query(User).filter(User.telegram_id == callback_or_message.from_user.id).first()
    user_session.close()
    lang = user.language if user else "ru"

    if isinstance(callback_or_message, types.CallbackQuery):
        await callback_or_message.message.answer(t("med_added", lang), reply_markup=ReplyKeyboardRemove())
        chat = callback_or_message.message
    else:
        await callback_or_message.answer(t("med_added", lang), reply_markup=ReplyKeyboardRemove())
        chat = callback_or_message

    kb = main_menu_keyboard(user)
    await chat.answer(t("main_menu", lang), reply_markup=kb)

    await state.clear()

def register_handlers(dp: Dispatcher):
    dp.message.register(cmd_add_med, lambda m: m.text in ["➕ Добавить препарат", "➕ Add Medication"])
    dp.message.register(cancel_medication, StateFilter(MedicationStates), lambda m: m.text.lower() in ["отмена", "cancel"])
    dp.message.register(process_name, StateFilter(MedicationStates.waiting_for_name))
    dp.message.register(process_dosage, StateFilter(MedicationStates.waiting_for_dosage))
    dp.callback_query.register(process_type, lambda c: c.data and c.data.startswith("medtype_"), StateFilter(MedicationStates.waiting_for_type))
    dp.message.register(process_type_text, StateFilter(MedicationStates.waiting_for_type))
    dp.message.register(process_times, StateFilter(MedicationStates.waiting_for_times))
    dp.message.register(process_conditions, StateFilter(MedicationStates.waiting_for_conditions))
    dp.callback_query.register(process_skip, lambda c: c.data and c.data.startswith("skp_"), StateFilter(MedicationStates.waiting_for_skip))
