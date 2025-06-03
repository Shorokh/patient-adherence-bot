import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DB_PATH = os.getenv("DB_PATH", "data/bot.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"
MAX_REMINDER_RETRIES = int(os.getenv("MAX_REMINDER_RETRIES", 3))
