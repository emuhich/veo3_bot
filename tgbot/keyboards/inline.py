from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


async def menu_kb():
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Тест", callback_data="test")
    return keyboard.adjust(1).as_markup()
