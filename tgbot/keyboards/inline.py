from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


async def menu_kb():
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Генерация видео", callback_data="generate_video")
    keyboard.button(text="Пополнение баланса", callback_data="topup_start")
    keyboard.button(text="Реферальная система", callback_data="referral_system")
    keyboard.button(text="Бесплатный ChatGPT", callback_data="free_chatgpt")
    keyboard.button(text="Поддержка", callback_data="support")
    return keyboard.adjust(1).as_markup()


async def back_to_menu_kb():
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="В меню", callback_data="back_to_menu")
    return keyboard.as_markup()


async def video_format_kb():
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Fast Version", callback_data="fast_version")
    keyboard.button(text="Quality Version", callback_data="quality_version")
    keyboard.button(text="В меню", callback_data="back_to_menu")
    return keyboard.adjust(1).as_markup()


async def side_orientation_kb():
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="16:9", callback_data="side_16_9")
    keyboard.button(text="9:16", callback_data="side_9_16")
    keyboard.button(text="В меню", callback_data="back_to_menu")
    return keyboard.adjust(1).as_markup()


async def wait_photo_kb():
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Пропустить", callback_data="skip_photo")
    keyboard.button(text="В меню", callback_data="back_to_menu")
    return keyboard.adjust(1).as_markup(resize_keyboard=True, one_time_keyboard=True)


async def video_count_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="1 видео", callback_data="vid_cnt_1")
    kb.button(text="2 видео", callback_data="vid_cnt_2")
    kb.button(text="3 видео", callback_data="vid_cnt_3")
    kb.button(text="В меню", callback_data="back_to_menu")
    return kb.adjust(3, 1).as_markup()


COIN_PRESETS = [1, 3, 5, 10, 20]


async def topup_amount_kb():
    kb = InlineKeyboardBuilder()
    for c in COIN_PRESETS:
        kb.button(text=f"{c} мон", callback_data=f"topup_amt_{c}")
    kb.button(text="Другое", callback_data="topup_amt_custom")
    kb.button(text="В меню", callback_data="back_to_menu")
    return kb.adjust(5, 1, 1).as_markup()


async def topup_method_kb(payment_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="YooKassa", callback_data=f"topup_mtd_yk_{payment_id}")
    kb.button(text="CryptoBot (USDT)", callback_data=f"topup_mtd_cb_{payment_id}")
    kb.button(text="Telegram Stars", callback_data=f"topup_mtd_ts_{payment_id}")
    kb.button(text="Отмена", callback_data=f"topup_cancel_{payment_id}")
    return kb.adjust(1).as_markup()


async def topup_check_kb(payment_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="Проверить оплату", callback_data=f"topup_check_{payment_id}")
    kb.button(text="Отмена", callback_data=f"topup_cancel_{payment_id}")
    return kb.adjust(1).as_markup()
