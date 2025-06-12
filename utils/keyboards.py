from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.i18n import t

def build_reminder_keyboard(reminder_id: int, lang: str) -> InlineKeyboardMarkup:
    """
    Клавиатура для напоминания. После первого нажатия кнопки (принял/пропустил)
    клавиатура должна быть удалена обработчиком, чтобы избежать повторных отметок.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t("btn_mark_taken", lang), callback_data=f"taken:{reminder_id}"),
                InlineKeyboardButton(text=t("btn_skip", lang), callback_data=f"skipped:{reminder_id}")
            ]
        ]
    )
