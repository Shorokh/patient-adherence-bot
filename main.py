import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from scheduler import start_scheduler

# Хэндлеры
from handlers.start import register_handlers as register_start_handlers
from handlers.medication import register_handlers as register_med_handlers
from handlers import menu, settings
from handlers.reminder_callbacks.handlers import register_handlers as register_reminder_handlers

async def main():
    # Выводим сообщение о запуске
    print(">>> Запуск бота patient-adherence-bot...")

    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрируем хэндлеры в нужном порядке:
    register_start_handlers(dp)
    register_med_handlers(dp)            # Добавление препарата
    menu.register_handlers(dp)            # Главное меню
    register_reminder_handlers(dp)        # Обработка «Принял/Пропустил»
    settings.register_handlers(dp)        # Настройки

    # Запускаем планировщик напоминаний
    start_scheduler()

    # Ещё один вывод, чтобы понимать, что диспетчер и планировщик подняты
    print(">>> Бот готов к работе. Ожидаем обновления...")

    # Запускаем polling
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
