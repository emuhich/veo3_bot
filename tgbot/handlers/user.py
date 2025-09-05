from aiogram import Router, Bot, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from admin_panel.telebot.models import Client, Referral
from tgbot.keyboards.inline import menu_kb, back_to_menu_kb
from tgbot.models.db_commands import select_client, create_client, AsyncDatabaseOperations

user_router = Router()

REF_INVITER_REWARD = 3
REF_INVITED_BONUS = 1


@user_router.message(Command(commands=["start"]))
async def user_start(message: Message, state: FSMContext):
    await state.clear()
    ref_code = None
    if message.text and " " in message.text:
        parts = message.text.split(maxsplit=1)
        if len(parts) == 2:
            ref_code = parts[1].strip()

    user: Client = await select_client(message.chat.id)
    is_new = False
    if not user:
        await create_client(
            message.from_user.username,
            message.chat.id,
            message.from_user.url,
            message.from_user.full_name,
        )
        user = await select_client(message.chat.id)
        is_new = True

    # Генерируем код если отсутствует
    if not user.referral_code:
        # синхронный метод модели вызовем в отдельном потоке, либо просто допустим sync (коротко)
        from asgiref.sync import sync_to_async
        await sync_to_async(user.ensure_referral_code)()

    # Обработка реферала только если новый пользователь и есть код
    if is_new and ref_code:
        inviters = await AsyncDatabaseOperations.get_objects_filter(Client, referral_code=ref_code)
        inviter = inviters[0] if inviters else None
        if inviter and inviter.id != user.id:
            # Проверка, что ещё нет связи
            existing = await AsyncDatabaseOperations.get_objects_filter(Referral, invited=user)
            if not existing:
                # Создание
                await AsyncDatabaseOperations.create_object(
                    Referral,
                    inviter=inviter,
                    invited=user,
                    reward_coins=REF_INVITER_REWARD,
                    invited_bonus=REF_INVITED_BONUS
                )
                # Начисления
                inviter.balance += REF_INVITER_REWARD
                inviter.referral_earnings += REF_INVITER_REWARD
                inviter.save(update_fields=["balance", "referral_earnings"])
                user.balance += REF_INVITED_BONUS
                user.save(update_fields=["balance"])

                try:
                    await message.bot.send_message(
                        inviter.telegram_id,
                        f"🎉 Новый реферал: @{user.username or user.telegram_id}. "
                        f"+{REF_INVITER_REWARD} монет. Баланс: {inviter.balance}"
                    )
                except Exception:
                    pass
                await message.answer(
                    f"Вы пришли по реферальной ссылке. Вам начислено +{REF_INVITED_BONUS} монета(ы). "
                    f"Ваш баланс: {user.balance}"
                )

    welcome_text = (
        "👋 Добро пожаловать в Veo3!\n"
        "За пару минут ты создашь видео из текста или фото.\n\n"
        "Что умею:\n"
        "• 🎬 Генерация роликов (3 уровня качества)\n"
        "• 🖼 Поддержка фото и стилей\n"
        "• 🔊 Озвучка (в Ultra/Pro)\n"
        "• 💎 Реферальные бонусы и акции\n\n"
        f"💰 Баланс: {user.balance} мон."
    )

    await message.answer(text=welcome_text, reply_markup=await menu_kb())


@user_router.callback_query(F.data == "back_to_menu")
async def back_to_manu(call: CallbackQuery, state: FSMContext):
    await call.message.delete()
    await user_start(call.message, state)


@user_router.callback_query(F.data == "support")
async def support_info(call: CallbackQuery):
    text = (
        "Если у вас есть вопросы или нужна помощь, вы можете связаться с нами:\n\n"
        "💬 Telegram: @market_brains_ai\n"
    )
    await call.message.edit_text(text, reply_markup=await back_to_menu_kb())
