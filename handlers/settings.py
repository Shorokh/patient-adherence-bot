# Файл: handlers/settings.py

from aiogram import types, Dispatcher
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

from utils.db import SessionLocal
from models.user import User
from handlers.menu import main_menu_keyboard

# 1) FSM-состояния для настроек
class SettingsStates(StatesGroup):
    choosing_action = State()
    changing_language = State()
    changing_ui = State()
    changing_role = State()


# 2) Клавиатура «⚙️ Настройки»
def settings_keyboard() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Сменить язык")],
            [KeyboardButton(text="Сменить режим UI")],
            [KeyboardButton(text="Изменить роль")],
            [KeyboardButton(text="Назад в главное")]  # чтобы вернуться
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return kb


# 3) Inline-клавиатура для выбора языка
def language_inline_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Русский", callback_data="set_lang_ru"),
            InlineKeyboardButton(text="English", callback_data="set_lang_en"),
        ]
    ])


# 4) Inline-клавиатура для выбора UI-режима
def ui_inline_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Стандартный", callback_data="set_ui_standard"),
            InlineKeyboardButton(text="Упрощённый", callback_data="set_ui_simple"),
        ]
    ])


# 5) Inline-клавиатура для выбора роли
def role_inline_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Пациент", callback_data="set_role_patient"),
            InlineKeyboardButton(text="Помощник", callback_data="set_role_assistant"),
        ]
    ])


# === ХЭНДЛЕР: открытие меню настроек ===
async def cmd_settings(message: types.Message, state: FSMContext):
    session = SessionLocal()
    user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
    session.close()

    if not user:
        await message.answer("Сначала зарегистрируйтесь – введите /start")
        return

    # Показываем Reply-клавиатуру настроек
    await message.answer("⚙️ Настройки:", reply_markup=settings_keyboard())
    await state.set_state(SettingsStates.choosing_action)


# === ШАГ: обработка выбора действия в настройках ===
async def process_settings_choice(message: types.Message, state: FSMContext):
    text = message.text
    if text == "Сменить язык":
        await message.answer("Выберите язык:", reply_markup=language_inline_kb())
        await state.set_state(SettingsStates.changing_language)
    elif text == "Сменить режим UI":
        await message.answer("Выберите режим интерфейса:", reply_markup=ui_inline_kb())
        await state.set_state(SettingsStates.changing_ui)
    elif text == "Изменить роль":
        await message.answer("Выберите роль:", reply_markup=role_inline_kb())
        await state.set_state(SettingsStates.changing_role)
    elif text == "Назад в главное":
        # Сброс состояния и возврат в главное меню
        await state.clear()
        session = SessionLocal()
        user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
        session.close()
        kb = main_menu_keyboard(user)
        await message.answer("Главное меню:", reply_markup=kb)
    else:
        # Если нажали что-то другое, просим выбрать снова
        await message.answer("Пожалуйста, выберите один из пунктов меню настроек.")


# === ШАГ: сохранить новый язык ===
async def set_language(callback: types.CallbackQuery, state: FSMContext):
    lang = "ru" if callback.data.endswith("_ru") else "en"
    session = SessionLocal()
    user = session.query(User).filter(User.telegram_id == callback.from_user.id).first()
    if user:
        user.language = lang
        session.add(user)
        session.commit()
    session.close()

    # Сообщаем об успехе и возвращаемся в меню настроек
    await callback.message.edit_text(f"Язык изменён на {'Русский' if lang=='ru' else 'English'}.")
    await callback.answer()

    await callback.message.answer("⚙️ Настройки:", reply_markup=settings_keyboard())
    await state.set_state(SettingsStates.choosing_action)


# === ШАГ: сохранить новый UI-режим ===
async def set_ui_mode(callback: types.CallbackQuery, state: FSMContext):
    ui_mode = "standard" if callback.data.endswith("_standard") else "simple"
    session = SessionLocal()
    user = session.query(User).filter(User.telegram_id == callback.from_user.id).first()
    if user:
        user.ui_mode = ui_mode
        session.add(user)
        session.commit()
    session.close()

    await callback.message.edit_text(f"Режим интерфейса установлен на {'Стандартный' if ui_mode=='standard' else 'Упрощённый'}.")
    await callback.answer()

    await callback.message.answer("⚙️ Настройки:", reply_markup=settings_keyboard())
    await state.set_state(SettingsStates.choosing_action)


# === ШАГ: сохранить новую роль ===
async def set_role(callback: types.CallbackQuery, state: FSMContext):
    role = "patient" if callback.data.endswith("_patient") else "assistant"
    session = SessionLocal()
    user = session.query(User).filter(User.telegram_id == callback.from_user.id).first()
    if user:
        user.role = role
        session.add(user)
        session.commit()
    session.close()

    await callback.message.edit_text(f"Роль изменена на {'Пациент' if role=='patient' else 'Помощник'}.")
    await callback.answer()

    await callback.message.answer("⚙️ Настройки:", reply_markup=settings_keyboard())
    await state.set_state(SettingsStates.choosing_action)


# === ХЭНДЛЕР /profile (показ текущих настроек) ===
async def cmd_profile(message: types.Message):
    session = SessionLocal()
    user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
    session.close()

    if not user:
        await message.answer("❗️ Вы не зарегистрированы. Сначала выполните /start.")
        return

    text = (
        f"📋 Ваш профиль:\n"
        f"• Telegram ID: {user.telegram_id}\n"
        f"• Язык: {user.language}\n"
        f"• UI-режим: {user.ui_mode}\n"
        f"• Роль: {user.role}\n"
        f"• Часовой пояс: {user.timezone or 'не задан'}\n"
    )
    await message.answer(text)


# === РЕГИСТРАЦИЯ ВСЕХ ХЭНДЛЕРОВ ===
def register_handlers(dp: Dispatcher):
    # Открытие меню настроек
    dp.message.register(cmd_settings, lambda m: m.text == "⚙️ Настройки")

    # Обработка выбора пункта меню «Настройки»
    dp.message.register(
        process_settings_choice,
        StateFilter(SettingsStates.choosing_action)
    )

    # Inline-кнопки для языка
    dp.callback_query.register(
        set_language,
        lambda c: c.data and c.data.startswith("set_lang_"),
        StateFilter(SettingsStates.changing_language)
    )

    # Inline-кнопки для UI-режима
    dp.callback_query.register(
        set_ui_mode,
        lambda c: c.data and c.data.startswith("set_ui_"),
        StateFilter(SettingsStates.changing_ui)
    )

    # Inline-кнопки для роли
    dp.callback_query.register(
        set_role,
        lambda c: c.data and c.data.startswith("set_role_"),
        StateFilter(SettingsStates.changing_role)
    )

    # Хэндлер /profile
    dp.message.register(cmd_profile, lambda m: m.text == "/profile")
