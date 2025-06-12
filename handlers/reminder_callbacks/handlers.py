from aiogram import types, Dispatcher

from utils.db import SessionLocal
from models.reminder import Reminder
from models.medication import Medication
from models.intake_log import IntakeLog
from models.user import User
from utils.helpers import calculate_next_due_for_timezone
from utils.i18n import t

async def process_taken(callback: types.CallbackQuery):
    session = SessionLocal()
    rem = session.query(Reminder).filter(Reminder.id == int(callback.data.split(":")[1])).first()
    if not rem:
        await callback.answer("Reminder not found.")  # unlikely to localize here
        session.close()
        return

    user = session.query(User).filter(User.telegram_id == rem.medication.owner.telegram_id).first()
    lang = user.language
    log = IntakeLog(medication_id=rem.medication_id, status="taken")
    session.add(log)

    rem.retry_count = 0
    med = rem.medication
    if med.intake_type == "regular" and med.time_list:
        user_tz = session.query(User).filter(User.telegram_id == med.user_id).first()
        tz = user_tz.timezone or "+00:00"
        rem.next_due = calculate_next_due_for_timezone(med.time_list, tz)
    else:
        rem.is_active = False

    session.add(rem)
    session.commit()
    session.close()

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(t("took", lang))
    await callback.answer()

async def process_skipped(callback: types.CallbackQuery):
    session = SessionLocal()
    rem = session.query(Reminder).filter(Reminder.id == int(callback.data.split(":")[1])).first()
    if not rem:
        await callback.answer("Reminder not found.")
        session.close()
        return

    user = session.query(User).filter(User.telegram_id == rem.medication.owner.telegram_id).first()
    lang = user.language
    log = IntakeLog(medication_id=rem.medication_id, status="skipped")
    session.add(log)

    rem.retry_count = 0
    med = rem.medication
    # --- Новая логика для skip_behavior ---
    if hasattr(med, 'skip_behavior') and med.skip_behavior == "later":
        from datetime import datetime, timedelta
        rem.next_due = datetime.utcnow() + timedelta(hours=1)
        rem.is_active = True
        # Сбросить флаг удвоения, если был
        if hasattr(rem, 'double_next'):
            rem.double_next = False
    elif hasattr(med, 'skip_behavior') and med.skip_behavior == "double":
        # Установить флаг удвоения для следующего напоминания
        rem.double_next = True
        # Следующее напоминание по расписанию
        if med.intake_type == "regular" and med.time_list:
            user_tz = session.query(User).filter(User.telegram_id == med.user_id).first()
            tz = user_tz.timezone or "+00:00"
            rem.next_due = calculate_next_due_for_timezone(med.time_list, tz)
        else:
            rem.is_active = False
    elif med.intake_type == "regular" and med.time_list:
        user_tz = session.query(User).filter(User.telegram_id == med.user_id).first()
        tz = user_tz.timezone or "+00:00"
        rem.next_due = calculate_next_due_for_timezone(med.time_list, tz)
        # Сбросить флаг удвоения, если был
        if hasattr(rem, 'double_next'):
            rem.double_next = False
    else:
        rem.is_active = False

    session.add(rem)
    session.commit()
    session.close()

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(t("skipped", lang))
    await callback.answer()

async def process_situational(callback: types.CallbackQuery):
    session = SessionLocal()
    med = session.query(Medication).filter(Medication.id == int(callback.data.split(":")[1])).first()
    if not med:
        await callback.answer("Medication not found.")
        session.close()
        return

    user = session.query(User).filter(User.telegram_id == med.user_id).first()
    lang = user.language
    med_name = med.name
    log = IntakeLog(medication_id=med.id, status="taken")
    session.add(log)
    session.commit()
    session.close()

    await callback.message.answer(t("sit_taken", lang, name=med_name))
    await callback.answer()

def register_handlers(dp: Dispatcher):
    dp.callback_query.register(process_taken, lambda c: c.data and c.data.startswith("taken:"))
    dp.callback_query.register(process_skipped, lambda c: c.data and c.data.startswith("skipped:"))
    dp.callback_query.register(process_situational, lambda c: c.data and c.data.startswith("take_sit:"))
