# Файл: scheduler.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timezone
from aiogram import Bot
from config import BOT_TOKEN, MAX_REMINDER_RETRIES
from utils.db import SessionLocal
from models.reminder import Reminder
from models.medication import Medication
from utils.keyboards import build_reminder_keyboard

bot = Bot(token=BOT_TOKEN)


async def send_reminder(reminder, session):
    med = session.query(Medication).filter(Medication.id == reminder.medication_id).first()
    user = med.owner

    text = (
        f"🔔 Пора принять препарат: {med.name} ({med.dosage}).\n"
        f"Условия: {', '.join(med.conditions) if med.conditions else 'нет'}."
    )
    keyboard = build_reminder_keyboard(reminder.id)
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
        # Запускаем асинхронный send_reminder
        await send_reminder(rem, session)
        rem.retry_count += 1
        session.add(rem)

    session.commit()
    session.close()


def start_scheduler():
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(check_and_send_reminders, "interval", minutes=1)
    scheduler.start()
