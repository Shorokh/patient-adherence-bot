# Файл: handlers/menu.py

from aiogram import types, Dispatcher
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

from utils.db import SessionLocal
from models.user import User
from models.medication import Medication

def main_menu_keyboard(user: User) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить препарат")],
            [KeyboardButton(text="💊 Мои препараты")],
            [KeyboardButton(text="⚙️ Настройки")]
        ],
        resize_keyboard=True
    )
    return kb

async def show_main_menu(message: types.Message):
    session = SessionLocal()
    user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
    session.close()

    if not user:
        await message.answer("Сначала введите /start")
        return

    kb = main_menu_keyboard(user)
    await message.answer("Главное меню:", reply_markup=kb)


# === Обновленный хэндлер «Мои препараты» ===
async def show_my_medications(message: types.Message):
    session = SessionLocal()
    user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
    if not user:
        await message.answer("Сначала введите /start")
        session.close()
        return

    meds = session.query(Medication).filter(Medication.user_id == message.from_user.id).all()
    session.close()

    if not meds:
        await message.answer("ℹ️ У вас пока нет добавленных препаратов.")
        return

    # Отправляем по одному сообщению на каждый препарат
    for med in meds:
        text = f"• {med.name} — {med.dosage}\n"
        text += f"  Тип: {'Регулярный' if med.intake_type == 'regular' else 'Ситуативный'}\n"
        if med.intake_type == "regular" and med.time_list:
            times = ", ".join(med.time_list)
            text += f"  Время приёма (чч:мм): {times}\n"
        if med.conditions:
            cond = ", ".join(med.conditions)
            text += f"  Условия: {cond}\n"
        if med.skip_behavior and med.intake_type == "regular":
            skip_map = {
                "double": "Удвоить",
                "skip": "Пропустить",
                "none": "Без напоминаний"
            }
            text += f"  При пропуске: {skip_map.get(med.skip_behavior, med.skip_behavior)}\n"

        # Для ситуативных добавляем Inline-кнопку «Отметить приём»
        if med.intake_type == "situational":
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Отметить приём", callback_data=f"take_sit:{med.id}")]
            ])
            await message.answer(text, reply_markup=kb)
        else:
            # Просто текст без кнопок
            await message.answer(text)


def register_handlers(dp: Dispatcher):
    dp.message.register(
        show_main_menu,
        lambda m: m.text == "Главное меню" or m.text == "Меню"
    )
    dp.message.register(
        show_my_medications,
        lambda m: m.text == "💊 Мои препараты"
    )
