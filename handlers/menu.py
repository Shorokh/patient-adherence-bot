from aiogram import types, Dispatcher
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

from utils.db import SessionLocal
from models.user import User
from models.medication import Medication
from utils.i18n import t

def main_menu_keyboard(user: User) -> ReplyKeyboardMarkup:
    lang = user.language
    buttons = [
        [KeyboardButton(text="➕ " + ("Добавить препарат" if lang == "ru" else "Add Medication"))],
        [KeyboardButton(text="💊 " + ("Мои препараты" if lang == "ru" else "My Medications"))],
        [KeyboardButton(text="⚙️ " + ("Настройки" if lang == "ru" else "Settings"))]
    ]
    # Если режим интерфейса стандартный, добавляем кнопку «Статистика»
    if user.ui_mode == "standard":
        buttons.insert(2, [KeyboardButton(text="📈 " + ("Статистика" if lang == "ru" else "Statistics"))])

    kb = ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True
    )
    return kb

async def show_main_menu(message: types.Message):
    session = SessionLocal()
    user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
    session.close()

    if not user:
        await message.answer(t("first_register", "ru"))
        return

    kb = main_menu_keyboard(user)
    await message.answer(t("main_menu", user.language), reply_markup=kb)

async def show_my_medications(message: types.Message):
    session = SessionLocal()
    user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
    if not user:
        await message.answer(t("first_register", "ru"))
        session.close()
        return

    meds = session.query(Medication).filter(Medication.user_id == message.from_user.id).all()
    session.close()

    if not meds:
        await message.answer(t("my_meds_empty", user.language))
        return

    for med in meds:
        lang = user.language
        text = f"• {med.name} — {med.dosage}\n"
        text += f"  {'Регулярный' if med.intake_type == 'regular' and lang == 'ru' else 'Regular' if med.intake_type == 'regular' else 'Ситуативный' if lang == 'ru' else 'Situational'}\n"
        if med.intake_type == "regular" and med.time_list:
            times = ", ".join(med.time_list)
            key = "Время приёма (чч:мм): " if lang == "ru" else "Intake times (HH:MM): "
            text += f"  {key}{times}\n"
        if med.conditions:
            cond = ", ".join(med.conditions)
            key = "Условия: " if lang == "ru" else "Conditions: "
            text += f"  {key}{cond}\n"
        if med.skip_behavior and med.intake_type == "regular":
            skip_map = {
                "double": "Удвоить" if lang == "ru" else "Double",
                "skip": "Пропустить" if lang == "ru" else "Skip",
                "none": "Без напоминаний" if lang == "ru" else "No reminders"
            }
            key = "При пропуске: " if lang == "ru" else "On skip: "
            text += f"  {key}{skip_map.get(med.skip_behavior)}\n"

        if med.intake_type == "situational":
            btn_text = "✅ " + ("Отметить приём" if lang == "ru" else "Mark Taken")
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=btn_text, callback_data=f"take_sit:{med.id}")]
            ])
            await message.answer(text, reply_markup=kb)
        else:
            await message.answer(text)

async def show_statistics(message: types.Message):
    session = SessionLocal()
    user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
    if not user:
        await message.answer(t("first_register", "ru"))
        session.close()
        return

    meds = session.query(Medication).filter(Medication.user_id == user.telegram_id).all()
    if not meds:
        session.close()
        await message.answer(t("my_meds_empty", user.language))
        return

    lines = []
    total_taken = 0
    total_skipped = 0
    from models.intake_log import IntakeLog
    for med in meds:
        # Подсчет по каждому препарату
        taken_count = session.query(IntakeLog).filter(
            IntakeLog.medication_id == med.id,
            IntakeLog.status == "taken"
        ).count()
        skipped_count = session.query(IntakeLog).filter(
            IntakeLog.medication_id == med.id,
            IntakeLog.status == "skipped"
        ).count()
        total_taken += taken_count
        total_skipped += skipped_count

        if user.language == "ru":
            lines.append(f"• {med.name}: принято {taken_count}, пропущено {skipped_count}")
        else:
            lines.append(f"• {med.name}: taken {taken_count}, skipped {skipped_count}")

    session.close()

    # Общая статистика
    if total_taken + total_skipped > 0:
        adherence = (total_taken / (total_taken + total_skipped)) * 100
        if user.language == "ru":
            overall = f"Общая успеваемость: {total_taken}✅, {total_skipped}❌. Процент: {adherence:.1f}%"
        else:
            overall = f"Overall adherence: {total_taken}✅, {total_skipped}❌. Rate: {adherence:.1f}%"
    else:
        overall = t("my_meds_empty", user.language)

    await message.answer("\n".join(lines + [overall]))

def register_handlers(dp: Dispatcher):
    dp.message.register(show_main_menu, lambda m: m.text in ["Главное меню", "Menu"])
    dp.message.register(show_my_medications, lambda m: m.text in ["💊 Мои препараты", "💊 My Medications"])
    dp.message.register(show_statistics, lambda m: m.text in ["📈 Статистика", "📈 Statistics"])
