import os

# Токен бота (можно задать в .env или напрямую здесь)
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN_HERE")

# Путь к файлу SQLite
DB_PATH = os.getenv("DB_PATH", "data/bot.db")

# Язык по умолчанию
DEFAULT_LANGUAGE = "ru"

# Режим интерфейса по умолчанию (“standard” или “simple”)
DEFAULT_UI_MODE = "standard"

# Максимальное число повторных напоминаний, если пользователь не ответил
MAX_REMINDER_RETRIES = 3
