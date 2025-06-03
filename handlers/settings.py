from aiogram import types, Dispatcher
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

from utils.db import SessionLocal
from models.user import User
from handlers.menu import main_menu_keyboard
from utils.i18n import t

class SettingsStates(StatesGroup):
    choosing_action = State()
    changing_language = State()
    changing_ui = State()
    changing_role = State()

def settings_keyboard(lang: str) -> ReplyKeyboardMarkup:
    if lang == "ru":
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Сменить язык")],
                [KeyboardButton(text="Сменить режим UI")],
                [KeyboardButton(text="Изменить роль")],
                [KeyboardButton(text="Назад в главное")]
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    else:
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Change Language")],
                [KeyboardButton(text="Change UI Mode")],
                [KeyboardButton(text="Change Role")],
                [KeyboardButton(text="Back to Main")]
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    return kb

def language_inline_kb(lang: str) -> InlineKeyboardMarkup:
    if lang == "ru":
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Русский", callback_data="set_lang_ru"),
                InlineKeyboardButton(text="English", callback_data="set_lang_en")
            ]
        ])
    else:
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Русский", callback_data="set_lang_ru"),
                InlineKeyboardButton(text="English", callback_data="set_lang_en")
            ]
        ])

def ui_inline_kb(lang: str) -> InlineKeyboardMarkup:
    if lang == "ru":
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Стандартный", callback_data="set_ui_standard"),
                InlineKeyboardButton(text="Упрощённый", callback_data="set_ui_simple")
            ]
        ])
    else:
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Standard", callback_data="set_ui_standard"),
                InlineKeyboardButton(text="Simple", callback_data="set_ui_simple")
            ]
        ])

def role_inline_kb(lang: str) -> InlineKeyboardMarkup:
    if lang == "ru":
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Пациент", callback_data="set_role_patient"),
                InlineKeyboardButton(text="Помощник", callback_data="set_role_assistant")
            ]
        ])
    else:
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Patient", callback_data="set_role_patient"),
                InlineKeyboardButton(text="Assistant", callback_data="set_role_assistant")
            ]
        ])

async def cmd_settings(message: types.Message, state: FSMContext):
    session = SessionLocal()
    user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
    session.close()

    if not user:
        await message.answer(t("first_register", "ru"))
        return

    lang = user.language
    await message.answer(t("settings_title", lang), reply_markup=settings_keyboard(lang))
    await state.set_state(SettingsStates.choosing_action)

async def process_settings_choice(message: types.Message, state: FSMContext):
    session = SessionLocal()
    user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
    session.close()
    lang = user.language

    text = message.text
    if (lang == "ru" and text == "Сменить язык") or (lang == "en" and text == "Change Language"):
        await message.answer(t("choose_language", lang), reply_markup=language_inline_kb(lang))
        await state.set_state(SettingsStates.changing_language)
    elif (lang == "ru" and text == "Сменить режим UI") or (lang == "en" and text == "Change UI Mode"):
        await message.answer(t("choose_ui", lang), reply_markup=ui_inline_kb(lang))
        await state.set_state(SettingsStates.changing_ui)
    elif (lang == "ru" and text == "Изменить роль") or (lang == "en" and text == "Change Role"):
        await message.answer(t("choose_role", lang), reply_markup=role_inline_kb(lang))
        await state.set_state(SettingsStates.changing_role)
    elif (lang == "ru" and text == "Назад в главное") or (lang == "en" and text == "Back to Main"):
        await state.clear()
        session = SessionLocal()
        user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
        session.close()
        kb = main_menu_keyboard(user)
        await message.answer(t("main_menu", lang), reply_markup=kb)
    else:
        await message.answer(t("choose_setting", lang))

async def set_language(callback: types.CallbackQuery, state: FSMContext):
    lang = "ru" if callback.data.endswith("_ru") else "en"
    session = SessionLocal()
    user = session.query(User).filter(User.telegram_id == callback.from_user.id).first()
    if user:
        user.language = lang
        session.add(user)
        session.commit()
    session.close()

    await callback.message.edit_text(t("settings_language", lang, language=("Русский" if lang == "ru" else "English")))
    await callback.answer()
    await callback.message.answer(t("settings_title", lang), reply_markup=settings_keyboard(lang))
    await state.set_state(SettingsStates.choosing_action)

async def set_ui_mode(callback: types.CallbackQuery, state: FSMContext):
    session = SessionLocal()
    user = session.query(User).filter(User.telegram_id == callback.from_user.id).first()
    lang = user.language
    ui_mode = "standard" if callback.data.endswith("_standard") else "simple"
    if user:
        user.ui_mode = ui_mode
        session.add(user)
        session.commit()
    session.close()

    ui_text = (
        "Стандартный" if ui_mode == "standard" and lang == "ru"
        else "Упрощённый" if ui_mode == "simple" and lang == "ru"
        else "Standard" if ui_mode == "standard"
        else "Simple"
    )
    await callback.message.edit_text(t("settings_ui", lang, ui_mode=ui_text))
    await callback.answer()
    await callback.message.answer(t("settings_title", lang), reply_markup=settings_keyboard(lang))
    await state.set_state(SettingsStates.choosing_action)

async def set_role(callback: types.CallbackQuery, state: FSMContext):
    session = SessionLocal()
    user = session.query(User).filter(User.telegram_id == callback.from_user.id).first()
    lang = user.language
    role = "patient" if callback.data.endswith("_patient") else "assistant"
    if user:
        user.role = role
        session.add(user)
        session.commit()
    session.close()

    role_text = (
        "Пациент" if role == "patient" and lang == "ru"
        else "Помощник" if role == "assistant" and lang == "ru"
        else "Patient" if role == "patient"
        else "Assistant"
    )
    await callback.message.edit_text(t("settings_role", lang, new_role=role_text))
    await callback.answer()
    await callback.message.answer(t("settings_title", lang), reply_markup=settings_keyboard(lang))
    await state.set_state(SettingsStates.choosing_action)

async def cmd_profile(message: types.Message):
    session = SessionLocal()
    user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
    session.close()

    if not user:
        await message.answer(t("profile_unregistered", "ru"))
        return

    lang = user.language
    text = t(
        "profile_text",
        lang,
        id=user.telegram_id,
        lang=user.language,
        ui=user.ui_mode,
        role=user.role,
        tz=user.timezone or ("не задан" if lang == "ru" else "not set")
    )
    await message.answer(text)

def register_handlers(dp: Dispatcher):
    dp.message.register(cmd_settings, lambda m: m.text in ["⚙️ Настройки", "⚙️ Settings"])
    dp.message.register(process_settings_choice, StateFilter(SettingsStates.choosing_action))
    dp.callback_query.register(set_language, lambda c: c.data and c.data.startswith("set_lang_"), StateFilter(SettingsStates.changing_language))
    dp.callback_query.register(set_ui_mode, lambda c: c.data and c.data.startswith("set_ui_"), StateFilter(SettingsStates.changing_ui))
    dp.callback_query.register(set_role, lambda c: c.data and c.data.startswith("set_role_"), StateFilter(SettingsStates.changing_role))
    dp.message.register(cmd_profile, lambda m: m.text == "/profile")
