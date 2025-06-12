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
        keyboard=[[KeyboardButton(text=t("btn_cancel", lang))]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def type_inline_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t("btn_regular", lang), callback_data="medtype_regular"),
            InlineKeyboardButton(text=t("btn_situational", lang), callback_data="medtype_situational")
        ]
    ])

def skip_inline_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t("btn_later", lang), callback_data="skp_later"),
            InlineKeyboardButton(text=t("btn_skip", lang), callback_data="skp_skip")
        ],
        [
            InlineKeyboardButton(text=t("btn_double", lang), callback_data="skp_double"),
            InlineKeyboardButton(text=t("skip_other", lang), callback_data="skp_other")
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
    cancel_values = [t("btn_cancel", l) for l in ["ru", "en"]]
    if text.lower() in [v.lower() for v in cancel_values]:
        return await cancel_medication(message, state)

    # Если редактируем, то разрешаем оставить текущее значение
    data = await state.get_data()
    if data.get("edit_med_id") and (not text or text == data.get("name", "")):
        await state.update_data(name=data.get("name", ""))
    else:
        await state.update_data(name=text)
    await message.answer(t("enter_dosage", lang), reply_markup=cancel_keyboard(lang))
    await state.set_state(MedicationStates.waiting_for_dosage)

async def process_dosage(message: types.Message, state: FSMContext):
    session = SessionLocal()
    user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
    session.close()
    lang = user.language if user else "ru"

    text = message.text.strip()
    cancel_values = [t("btn_cancel", l) for l in ["ru", "en"]]
    if text.lower() in [v.lower() for v in cancel_values]:
        return await cancel_medication(message, state)

    data = await state.get_data()
    if data.get("edit_med_id") and (not text or text == data.get("dosage", "")):
        await state.update_data(dosage=data.get("dosage", ""))
    else:
        await state.update_data(dosage=text)
    await message.answer(t("choose_type", lang), reply_markup=type_inline_kb(lang))
    await state.set_state(MedicationStates.waiting_for_type)

async def process_type_text(message: types.Message, state: FSMContext):
    session = SessionLocal()
    user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
    session.close()
    lang = user.language if user else "ru"

    text = message.text.strip().lower()
    cancel_values = [t("btn_cancel", l).lower() for l in ["ru", "en"]]
    if text in cancel_values:
        return await cancel_medication(message, state)

    valid_inputs = [t("btn_regular", lang).lower(), t("btn_situational", lang).lower()]
    if text not in valid_inputs:
        await message.answer(t("choose_type", lang), reply_markup=type_inline_kb(lang))
        return

    intake_type = "regular" if text == t("btn_regular", lang).lower() else "situational"
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
    cancel_values = [t("btn_cancel", l) for l in ["ru", "en"]]
    if text.lower() in [v.lower() for v in cancel_values]:
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
    cancel_values = [t("btn_cancel", l) for l in ["ru", "en"]]
    if text.lower() in [v.lower() for v in cancel_values]:
        return await cancel_medication(message, state)

    none_values = ["нет", "none"] + [t("btn_none", l).lower() for l in ["ru", "en"]]
    cond_text = text.lower()
    conditions = [] if cond_text in none_values else [c.strip() for c in text.split(",")]
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
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await save_medication(callback_or_message=callback, state=state)
    await callback.answer()

async def save_medication(callback_or_message, state: FSMContext):
    data = await state.get_data()
    session = SessionLocal()
    edit_med_id = data.get("edit_med_id")
    if edit_med_id:
        # Редактирование существующего препарата
        med = session.query(Medication).filter(Medication.id == edit_med_id).first()
        if med:
            med.name = data["name"]
            med.dosage = data["dosage"]
            med.intake_type = data["intake_type"]
            med.time_list = data.get("times", [])
            med.conditions = data.get("conditions", [])
            med.skip_behavior = data.get("skip_behavior", "")
            session.add(med)
            session.commit()
            # Обновить напоминание, если регулярный
            if med.intake_type == "regular" and med.time_list:
                rem = session.query(Reminder).filter(Reminder.medication_id == med.id).first()
                user = session.query(User).filter(User.telegram_id == callback_or_message.from_user.id).first()
                tz = user.timezone or "+00:00"
                next_due_utc = calculate_next_due_for_timezone(med.time_list, tz)
                if rem:
                    rem.next_due = next_due_utc
                    rem.retry_count = 0
                    rem.is_active = True
                    session.add(rem)
                else:
                    rem = Reminder(
                        medication_id=med.id,
                        next_due=next_due_utc,
                        retry_count=0,
                        is_active=True
                    )
                    session.add(rem)
                session.commit()
            elif med.intake_type == "situational":
                # Удалить напоминание, если был
                rem = session.query(Reminder).filter(Reminder.medication_id == med.id).first()
                if rem:
                    session.delete(rem)
                    session.commit()
        session.close()
        from handlers.menu import main_menu_keyboard
        user_session = SessionLocal()
        user = user_session.query(User).filter(User.telegram_id == callback_or_message.from_user.id).first()
        user_session.close()
        lang = user.language if user else "ru"
        if isinstance(callback_or_message, types.CallbackQuery):
            await callback_or_message.message.answer(("Изменения сохранены." if lang == "ru" else "Changes saved."), reply_markup=ReplyKeyboardRemove())
            chat = callback_or_message.message
        else:
            await callback_or_message.answer(("Изменения сохранены." if lang == "ru" else "Changes saved."), reply_markup=ReplyKeyboardRemove())
            chat = callback_or_message
        kb = main_menu_keyboard(user)
        await chat.answer(t("main_menu", lang), reply_markup=kb)
        await state.clear()
        return
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
    add_med_texts = [t("btn_add_med", lang) for lang in ["ru", "en"]]
    cancel_texts = [t("btn_cancel", lang).lower() for lang in ["ru", "en"]]
    dp.message.register(cmd_add_med, lambda m: m.text in add_med_texts)
    dp.message.register(cancel_medication, StateFilter(MedicationStates), lambda m: m.text.lower() in cancel_texts)
    dp.message.register(process_name, StateFilter(MedicationStates.waiting_for_name))
    dp.message.register(process_dosage, StateFilter(MedicationStates.waiting_for_dosage))
    dp.callback_query.register(process_type, lambda c: c.data and c.data.startswith("medtype_"), StateFilter(MedicationStates.waiting_for_type))
    dp.message.register(process_type_text, StateFilter(MedicationStates.waiting_for_type))
    dp.message.register(process_times, StateFilter(MedicationStates.waiting_for_times))
    dp.message.register(process_conditions, StateFilter(MedicationStates.waiting_for_conditions))
    dp.callback_query.register(process_skip, lambda c: c.data and c.data.startswith("skp_"), StateFilter(MedicationStates.waiting_for_skip))
