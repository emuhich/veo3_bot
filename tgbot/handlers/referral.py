from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram import Bot
from admin_panel.telebot.models import Client, Referral
from tgbot.models.db_commands import select_client, AsyncDatabaseOperations
from tgbot.keyboards.inline import back_to_menu_kb

referral_router = Router()


@referral_router.callback_query(F.data == "referral_system")
async def referral_info(call: CallbackQuery, bot: Bot):
    user: Client = await select_client(call.message.chat.id)
    if not user.referral_code:
        from asgiref.sync import sync_to_async
        await sync_to_async(user.ensure_referral_code)()
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start={user.referral_code}"
    refs = await AsyncDatabaseOperations.get_objects_filter(Referral, inviter=user)
    count = len(refs)
    earned = user.referral_earnings

    text = (
        "🔗 Ваша реферальная ссылка:\n"
        f"{link}\n\n"
        f"👥 Приглашено: {count}\n"
        f"💰 Заработано: {earned} монет\n\n"
    )
    try:
        await call.message.edit_text(text, reply_markup=await back_to_menu_kb())
    except Exception:
        await call.message.answer(text, reply_markup=await back_to_menu_kb())
