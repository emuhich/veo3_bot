from aiogram import Router, Bot, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from tgbot.keyboards.inline import menu_kb

user_router = Router()


@user_router.message(Command(commands=["start"]))
async def user_start(message: Message):
    await message.answer(text="Добро пожаловать", reply_markup=await menu_kb())


@user_router.callback_query(F.data == "test")
async def test_2(call: CallbackQuery, bot: Bot):
    pass
