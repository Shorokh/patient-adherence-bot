from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def build_reminder_keyboard(reminder_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Принял", callback_data=f"taken:{reminder_id}"),
                InlineKeyboardButton(text="❌ Пропустил", callback_data=f"skipped:{reminder_id}")
            ]
        ]
    )
