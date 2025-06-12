from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timezone
from aiogram import Bot
from config import BOT_TOKEN, MAX_REMINDER_RETRIES, REMINDER_INTERVAL_MINUTES
from utils.db import SessionLocal
from models.reminder import Reminder
from models.medication import Medication
from utils.keyboards import build_reminder_keyboard

bot = Bot(token=BOT_TOKEN)

async def send_reminder(reminder, session):
    med = session.query(Medication).filter(Medication.id == reminder.medication_id).first()
    user = med.owner
    lang = user.language
    conditions = ", ".join(med.conditions) if med.conditions else "none"
    from utils.i18n import t
    # --- Учет удвоенной дозы ---
    double_dose = getattr(reminder, 'double_next', False)
    dosage = med.dosage
    if double_dose:
        if lang == "ru":
            dosage = f"{dosage} (двойная доза!)"
        else:
            dosage = f"{dosage} (double dose!)"
        reminder.double_next = False  # сбрасываем флаг после напоминания
        session.add(reminder)
        session.commit()
    text = t("reminder_text", lang, name=med.name, dosage=dosage, conditions=conditions)
    keyboard = build_reminder_keyboard(reminder.id, lang)
    await bot.send_message(chat_id=user.telegram_id, text=text, reply_markup=keyboard)

async def check_and_send_reminders():
    session = SessionLocal()
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    reminders = session.query(Reminder).filter(
        Reminder.next_due <= now_utc,
        Reminder.is_active == True,
        Reminder.retry_count < MAX_REMINDER_RETRIES
    ).all()

    for rem in reminders:
        await send_reminder(rem, session)
        rem.retry_count += 1
        session.add(rem)

    session.commit()
    session.close()

def start_scheduler():
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(check_and_send_reminders, "interval", minutes=REMINDER_INTERVAL_MINUTES)
    scheduler.start()
