# Файл: handlers/reminder_callbacks/handlers.py

from aiogram import types, Dispatcher

from utils.db import SessionLocal
from models.reminder import Reminder
from models.medication import Medication
from models.intake_log import IntakeLog
from models.user import User
from utils.helpers import calculate_next_due_for_timezone


async def process_taken(callback: types.CallbackQuery):
    reminder_id = int(callback.data.split(":")[1])
    session = SessionLocal()
    rem = session.query(Reminder).filter(Reminder.id == reminder_id).first()
    if not rem:
        await callback.answer("Напоминание не найдено.")
        session.close()
        return

    log = IntakeLog(medication_id=rem.medication_id, status="taken")
    session.add(log)

    rem.retry_count = 0
    med = rem.medication
    # Пересчитываем next_due для регулярных
    if med.intake_type == "regular" and med.time_list:
        user = session.query(User).filter(User.telegram_id == med.user_id).first()
        tz = user.timezone or "+00:00"
        rem.next_due = calculate_next_due_for_timezone(med.time_list, tz)
    else:
        rem.is_active = False

    session.add(rem)
    session.commit()
    session.close()

    await callback.message.answer("✅ Отмечено как «Принял».")
    await callback.answer()


async def process_skipped(callback: types.CallbackQuery):
    reminder_id = int(callback.data.split(":")[1])
    session = SessionLocal()
    rem = session.query(Reminder).filter(Reminder.id == reminder_id).first()
    if not rem:
        await callback.answer("Напоминание не найдено.")
        session.close()
        return

    log = IntakeLog(medication_id=rem.medication_id, status="skipped")
    session.add(log)

    rem.retry_count = 0
    med = rem.medication
    if med.intake_type == "regular" and med.time_list:
        user = session.query(User).filter(User.telegram_id == med.user_id).first()
        tz = user.timezone or "+00:00"
        rem.next_due = calculate_next_due_for_timezone(med.time_list, tz)
    else:
        rem.is_active = False

    session.add(rem)
    session.commit()
    session.close()

    await callback.message.answer("❌ Отмечено как «Пропущено».")
    await callback.answer()


async def process_situational(callback: types.CallbackQuery):
    # callback.data = "take_sit:{med_id}"
    med_id = int(callback.data.split(":")[1])
    session = SessionLocal()
    med = session.query(Medication).filter(Medication.id == med_id).first()
    if not med:
        await callback.answer("Препарат не найден.")
        session.close()
        return

    # Сохраняем имя до закрытия сессии
    med_name = med.name

    log = IntakeLog(medication_id=med.id, status="taken")
    session.add(log)
    session.commit()
    session.close()

    await callback.message.answer(f"✅ Вы отметили приём препарата «{med_name}».")
    await callback.answer()


def register_handlers(dp: Dispatcher):
    dp.callback_query.register(
        process_taken,
        lambda c: c.data and c.data.startswith("taken:")
    )
    dp.callback_query.register(
        process_skipped,
        lambda c: c.data and c.data.startswith("skipped:")
    )
    dp.callback_query.register(
        process_situational,
        lambda c: c.data and c.data.startswith("take_sit:")
    )
