# Файл: handlers/start.py

from aiogram import types, Dispatcher
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from utils.db import SessionLocal
from models.user import User
from handlers.menu import main_menu_keyboard

class RegistrationStates(StatesGroup):
    language = State()
    ui_mode = State()
    role = State()
    timezone = State()   # шаг выбора часового пояса


def language_inline_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Русский", callback_data="lang_ru"),
            InlineKeyboardButton(text="English", callback_data="lang_en"),
        ]
    ])


def ui_mode_inline_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Стандартный", callback_data="ui_standard"),
            InlineKeyboardButton(text="Упрощённый", callback_data="ui_simple"),
        ]
    ])


def role_inline_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Пациент", callback_data="role_patient"),
            InlineKeyboardButton(text="Помощник", callback_data="role_assistant"),
        ]
    ])


# Заменяем на универсальную генерацию UTC−12…UTC+14
def timezone_inline_kb() -> InlineKeyboardMarkup:
    buttons = []
    # Создаём список кортежей (offset_string, callback_data)
    offsets = []
    for hour in range(-12, 15):  # от -12 до +14 включительно
        sign = "+" if hour >= 0 else "-"
        hh = abs(hour)
        offset_str = f"UTC{sign}{hh:02d}:00"
        offsets.append((offset_str, f"tz_{sign}{hh:02d}:00"))

    # Группируем по 4 кнопки в строку
    row = []
    for idx, (text, data) in enumerate(offsets, start=1):
        row.append(InlineKeyboardButton(text=text, callback_data=data))
        if idx % 4 == 0:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    # Добавляем кнопку «Другое» в последнюю строку
    buttons.append([InlineKeyboardButton(text="Другое", callback_data="tz_other")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def cmd_start(message: types.Message, state: FSMContext):
    session = SessionLocal()
    user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
    session.close()

    if user:
        await message.answer(
            "Вы уже зарегистрированы. Вот ваше главное меню:"
        )
        kb_main = main_menu_keyboard(user)
        await message.answer("Главное меню:", reply_markup=kb_main)
        return

    await message.answer(
        "Привет! Выберите язык:",
        reply_markup=language_inline_kb()
    )
    await state.set_state(RegistrationStates.language)


async def process_language(callback: types.CallbackQuery, state: FSMContext):
    lang = "ru" if callback.data.endswith("_ru") else "en"
    await state.update_data(language=lang)

    await callback.message.edit_text(
        "Теперь выберите режим интерфейса:",
        reply_markup=ui_mode_inline_kb()
    )
    await state.set_state(RegistrationStates.ui_mode)
    await callback.answer()


async def process_ui_mode(callback: types.CallbackQuery, state: FSMContext):
    ui_mode = "standard" if callback.data.endswith("_standard") else "simple"
    await state.update_data(ui_mode=ui_mode)

    await callback.message.edit_text(
        "И, наконец, выберите вашу роль:",
        reply_markup=role_inline_kb()
    )
    await state.set_state(RegistrationStates.role)
    await callback.answer()


async def process_role(callback: types.CallbackQuery, state: FSMContext):
    role = "patient" if callback.data.endswith("_patient") else "assistant"
    await state.update_data(role=role)

    await callback.message.edit_text(
        "Выберите свой часовой пояс:",
        reply_markup=timezone_inline_kb()
    )
    await state.set_state(RegistrationStates.timezone)
    await callback.answer()


async def process_timezone(callback: types.CallbackQuery, state: FSMContext):
    data = callback.data  # Например: "tz_+03:00", "tz_-05:00" или "tz_other"
    if data == "tz_other":
        await callback.message.edit_text(
            "Введите свой часовой пояс вручную (например, Europe/Moscow или +06:00):",
            reply_markup=None
        )
        await state.set_state(RegistrationStates.timezone)
        await callback.answer()
        return

    tz = data.replace("tz_", "")
    await state.update_data(timezone=tz)

    saved = await state.get_data()
    telegram_id = callback.from_user.id

    session = SessionLocal()
    new_user = User(
        telegram_id=telegram_id,
        language=saved["language"],
        ui_mode=saved["ui_mode"],
        role=saved["role"],
        timezone=saved["timezone"],
        assistant_id=None
    )
    session.add(new_user)
    session.commit()
    session.close()

    await callback.message.edit_text("Регистрация завершена! Вот ваше главное меню:")
    await state.clear()

    session = SessionLocal()
    user = session.query(User).filter(User.telegram_id == telegram_id).first()
    session.close()
    kb_main = main_menu_keyboard(user)
    await callback.message.answer("Главное меню:", reply_markup=kb_main)
    await callback.answer()


async def process_timezone_manual(message: types.Message, state: FSMContext):
    tz_text = message.text.strip()
    if len(tz_text) < 2:
        await message.answer("Неверный формат. Попробуйте снова или выберите из списка.")
        return

    await state.update_data(timezone=tz_text)
    saved = await state.get_data()
    telegram_id = message.from_user.id

    session = SessionLocal()
    new_user = User(
        telegram_id=telegram_id,
        language=saved["language"],
        ui_mode=saved["ui_mode"],
        role=saved["role"],
        timezone=saved["timezone"],
        assistant_id=None
    )
    session.add(new_user)
    session.commit()
    session.close()

    await message.answer("Регистрация завершена! Вот ваше главное меню:")
    await state.clear()

    session = SessionLocal()
    user = session.query(User).filter(User.telegram_id == telegram_id).first()
    session.close()
    kb_main = main_menu_keyboard(user)
    await message.answer("Главное меню:", reply_markup=kb_main)


def register_handlers(dp: Dispatcher):
    dp.message.register(cmd_start, Command(commands=["start"]))

    dp.callback_query.register(
        process_language,
        lambda c: c.data and c.data.startswith("lang_"),
        StateFilter(RegistrationStates.language)
    )

    dp.callback_query.register(
        process_ui_mode,
        lambda c: c.data and c.data.startswith("ui_"),
        StateFilter(RegistrationStates.ui_mode)
    )

    dp.callback_query.register(
        process_role,
        lambda c: c.data and c.data.startswith("role_"),
        StateFilter(RegistrationStates.role)
    )

    dp.callback_query.register(
        process_timezone,
        lambda c: c.data and c.data.startswith("tz_"),
        StateFilter(RegistrationStates.timezone)
    )

    dp.message.register(
        process_timezone_manual,
        StateFilter(RegistrationStates.timezone)
    )
