from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


async def menu_kb():
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Генерация видео", callback_data="generate_video")
    keyboard.button(text="Пополнение баланса", callback_data="top_up_balance")
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