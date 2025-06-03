import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from handlers import start, menu, medication, reminder_callbacks, settings, statistics
from scheduler import start_scheduler

async def main():
    print(">>> Запуск бота patient-adherence-bot...")
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    start.register_handlers(dp)
    menu.register_handlers(dp)
    medication.register_handlers(dp)
    reminder_callbacks.register_handlers(dp)
    settings.register_handlers(dp)
    statistics.register_handlers(dp)

    start_scheduler()

    print(">>> Бот готов к работе. Ожидаем обновления...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
