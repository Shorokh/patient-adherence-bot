from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


def build_reminder_keyboard(reminder_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Принял", callback_data=f"taken:{reminder_id}"),
                InlineKeyboardButton(text="❌ Пропустил", callback_data=f"skipped:{reminder_id}")
            ]
        ]
    )



def example_reply_kb():
    # Пример функции, создающей ReplyKeyboardMarkup
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Кнопка 1"), KeyboardButton(text="Кнопка 2")],
            [KeyboardButton(text="Кнопка 3")]
        ],
        resize_keyboard=True
    )
    return kb
