from aiogram import types, Dispatcher
from utils.db import SessionLocal
from models.user import User
from models.medication import Medication
from models.intake_log import IntakeLog
from utils.i18n import t

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

    for med in meds:
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

    if total_taken + total_skipped > 0:
        adherence = (total_taken / (total_taken + total_skipped)) * 100
        if user.language == "ru":
            overall = f"Общая успеваемость: {total_taken}✅, {total_skipped}❌. Процент: {adherence:.1f}%"
        else:
            overall = f"Overall adherence: {total_taken}✅, {total_skipped}❌. Rate: {adherence:.1f}%"
    else:
        overall = t("my_meds_empty", user.language)

    session.close()
    await message.answer("\n".join(lines + [overall]))

def register_handlers(dp: Dispatcher):
    dp.message.register(show_statistics, lambda m: m.text in ["📈 Статистика", "📈 Statistics"])
