from aiogram import Router, Bot, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from admin_panel.telebot.models import Client
from tgbot.keyboards.inline import menu_kb
from tgbot.models.db_commands import select_client, create_client

user_router = Router()


@user_router.message(Command(commands=["start"]))
async def user_start(message: Message, state: FSMContext):
    await state.clear()
    user: Client = await select_client(message.chat.id)
    if not user:
        await create_client(
            message.from_user.username,
            message.chat.id,
            message.from_user.url,
            message.from_user.full_name,
        )
    await message.answer(text="Добро пожаловать, выберите пункт меню", reply_markup=await menu_kb())


@user_router.callback_query(F.data == "back_to_menu")
async def back_to_manu(call: CallbackQuery, state: FSMContext):
    await call.message.delete()
    await user_start(call.message, state)
