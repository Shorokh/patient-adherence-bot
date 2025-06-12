from aiogram import types, Dispatcher
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from utils.db import SessionLocal
from models.user import User
from models.medication import Medication
from utils.i18n import t, SUPPORTED_LANGS
from handlers.medication import cancel_keyboard

# Кнопки главного меню (кроме Settings)
MAIN_CMD_KEYS = ["btn_add_med", "btn_my_meds", "btn_statistics", "btn_main_menu"]
MAIN_CMDS = {t(key, lang) for key in MAIN_CMD_KEYS for lang in SUPPORTED_LANGS}

# Текст кнопки Settings (обрабатывается в handlers/settings.py)
SETTINGS_BTN_TEXTS = {t("btn_settings", lang) for lang in SUPPORTED_LANGS}

# Вложенные кнопки внутри меню настроек
SETTINGS_CMD_KEYS = ["btn_change_language", "btn_change_ui", "btn_change_role", "btn_back_main"]
SETTINGS_CMDS = {t(key, lang) for key in SETTINGS_CMD_KEYS for lang in SUPPORTED_LANGS}


def main_menu_keyboard(user: User) -> ReplyKeyboardMarkup:
    lang = user.language
    buttons = [
        [KeyboardButton(text=t("btn_add_med", lang))],
        [KeyboardButton(text=t("btn_my_meds", lang))],
        [KeyboardButton(text=t("btn_settings", lang))]
    ]
    if user.ui_mode == "standard":
        buttons.insert(2, [KeyboardButton(text=t("btn_statistics", lang))])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


async def show_main_menu(message: types.Message):
    session = SessionLocal()
    user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
    session.close()

    if not user:
        await message.answer(t("first_register", "ru"))
        return

    kb = main_menu_keyboard(user)
    await message.answer(t("main_menu", user.language), reply_markup=kb)


async def show_my_medications(message: types.Message):
    session = SessionLocal()
    user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
    if not user:
        await message.answer(t("first_register", "ru"))
        session.close()
        return

    meds = session.query(Medication).filter(Medication.user_id == message.from_user.id).all()
    session.close()

    if not meds:
        await message.answer(t("my_meds_empty", user.language))
        return

    for med in meds:
        lang = user.language
        if med.intake_type == "regular":
            intake_type_text = t("intake_regular", lang)
        else:
            intake_type_text = t("intake_situational", lang)

        text = f"• {med.name} — {med.dosage}\n"
        text += f"  {intake_type_text}\n"

        if med.intake_type == "regular" and med.time_list:
            times = ", ".join(med.time_list)
            time_label = t("label_time", lang)
            text += f"  {time_label}{times}\n"

        if med.conditions:
            cond = ", ".join(med.conditions)
            cond_label = t("label_conditions", lang)
            text += f"  {cond_label}{cond}\n"

        if med.skip_behavior and med.intake_type == "regular":
            skip_map = {
                "later": t("skip_later", lang),
                "skip": t("skip_skip", lang),
                "double": t("skip_double", lang),
                "other": t("skip_other", lang)
            }
            skip_label = t("label_on_skip", lang)
            text += f"  {skip_label}{skip_map.get(med.skip_behavior, med.skip_behavior)}\n"

        manage_kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=t("btn_edit", lang), callback_data=f"edit_med:{med.id}"),
                InlineKeyboardButton(text=t("btn_delete", lang), callback_data=f"delete_med:{med.id}")
            ]
        ])

        if med.intake_type == "situational":
            btn_text = t("btn_mark_taken", lang)
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=btn_text, callback_data=f"take_sit:{med.id}")],
                [
                    InlineKeyboardButton(text=t("btn_edit", lang), callback_data=f"edit_med:{med.id}"),
                    InlineKeyboardButton(text=t("btn_delete", lang), callback_data=f"delete_med:{med.id}")
                ]
            ])
            await message.answer(text, reply_markup=kb)
        else:
            await message.answer(text, reply_markup=manage_kb)


async def fallback_to_main(message: types.Message, state: FSMContext):
    # Сбрасываем состояние FSM, если оно есть
    await state.clear()

    session = SessionLocal()
    user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
    session.close()

    if not user:
        await message.answer(t("first_register", "ru"))
        return

    kb = main_menu_keyboard(user)
    await message.answer(t("main_menu", user.language), reply_markup=kb)


# --- Заготовки для callback-обработчиков ---
async def process_delete_med(callback: types.CallbackQuery):
    med_id = int(callback.data.split(":")[1])
    session = SessionLocal()
    med = session.query(Medication).filter(Medication.id == med_id).first()
    user = session.query(User).filter(User.telegram_id == callback.from_user.id).first()
    lang = user.language if user else "ru"
    if not med or med.user_id != callback.from_user.id:
        await callback.answer("Not allowed.", show_alert=True)
        session.close()
        return
    # Подтверждение удаления
    confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t("btn_confirm_delete", lang), callback_data=f"confirm_delete_med:{med_id}"),
            InlineKeyboardButton(text=t("btn_cancel", lang), callback_data="cancel_delete_med")
        ]
    ])
    await callback.message.answer(t("confirm_delete_text", lang), reply_markup=confirm_kb)
    session.close()
    await callback.answer()

async def process_confirm_delete_med(callback: types.CallbackQuery):
    med_id = int(callback.data.split(":")[1])
    session = SessionLocal()
    med = session.query(Medication).filter(Medication.id == med_id).first()
    user = session.query(User).filter(User.telegram_id == callback.from_user.id).first()
    lang = user.language if user else "ru"
    if not med or med.user_id != callback.from_user.id:
        await callback.answer("Not allowed.", show_alert=True)
        session.close()
        return
    session.delete(med)
    session.commit()
    session.close()
    # Удаляем inline-клавиатуру у сообщения с вопросом
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await callback.message.answer(t("med_deleted", lang))
    await callback.answer()

async def process_cancel_delete_med(callback: types.CallbackQuery):
    lang = "ru"
    session = SessionLocal()
    user = session.query(User).filter(User.telegram_id == callback.from_user.id).first()
    if user:
        lang = user.language
    session.close()
    # Удаляем inline-клавиатуру у сообщения с вопросом
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await callback.message.answer(t("delete_cancelled", lang))
    await callback.answer()

async def process_edit_med(callback: types.CallbackQuery, state: FSMContext):
    med_id = int(callback.data.split(":")[1])
    session = SessionLocal()
    med = session.query(Medication).filter(Medication.id == med_id).first()
    user = session.query(User).filter(User.telegram_id == callback.from_user.id).first()
    lang = user.language if user else "ru"
    if not med or med.user_id != callback.from_user.id:
        await callback.answer("Not allowed.", show_alert=True)
        session.close()
        return
    # Сохраняем id редактируемого препарата в FSM
    await state.update_data(edit_med_id=med_id)
    # Заполняем FSM текущими значениями
    await state.update_data(name=med.name, dosage=med.dosage, intake_type=med.intake_type, times=med.time_list, conditions=med.conditions, skip_behavior=med.skip_behavior)
    session.close()
    # Запускаем FSM с шага изменения названия
    await callback.message.answer(t("edit_medication_text", lang), reply_markup=cancel_keyboard(lang))
    await state.set_state("MedicationStates:waiting_for_name")
    await callback.answer()


def register_handlers(dp: Dispatcher):
    # Обработчик «Главное меню» / «Menu»
    dp.message.register(
        show_main_menu,
        lambda m: m.text in [t("btn_main_menu", lang) for lang in SUPPORTED_LANGS]
    )

    # Обработчик «Мои препараты» / «My Medications»
    dp.message.register(
        show_my_medications,
        lambda m: m.text in [t("btn_my_meds", lang) for lang in SUPPORTED_LANGS]
    )

    # Обработчик выхода из настроек «Back to Main» (в тех же main_menu_keyboard)
    dp.message.register(
        show_main_menu,
        lambda m: m.text in [t("btn_back_main", lang) for lang in SUPPORTED_LANGS]
    )

    # fallback для ВСЕХ сообщений, когда нет активного состояния FSM:
    dp.message.register(
        fallback_to_main,
        StateFilter(None),
        lambda m: (
            m.text not in MAIN_CMDS
            and m.text not in SETTINGS_BTN_TEXTS
            and m.text not in SETTINGS_CMDS
        )
    )
    dp.callback_query.register(process_edit_med, lambda c: c.data and c.data.startswith("edit_med:"))
    dp.callback_query.register(process_delete_med, lambda c: c.data and c.data.startswith("delete_med:"))
    dp.callback_query.register(process_confirm_delete_med, lambda c: c.data and c.data.startswith("confirm_delete_med:"))
    dp.callback_query.register(process_cancel_delete_med, lambda c: c.data == "cancel_delete_med")
