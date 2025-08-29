from datetime import date

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from tgbot.config import Config
from tgbot.keyboards.inline import back_to_menu_kb
from tgbot.misc.states import ChatStates
from tgbot.models.db_commands import select_client

chat_router = Router()

MAX_TG_LEN = 4096
SAFE_SPLIT = 4000  # запас


def split_long(text: str):
    if len(text) <= MAX_TG_LEN:
        return [text]
    parts = []
    current = []
    current_len = 0
    for line in text.splitlines(keepends=True):
        if current_len + len(line) > SAFE_SPLIT:
            parts.append("".join(current))
            current = [line]
            current_len = len(line)
        else:
            current.append(line)
            current_len += len(line)
    if current:
        parts.append("".join(current))
    # Дополнительное дробление очень длинных без переносов
    final = []
    for p in parts:
        if len(p) <= MAX_TG_LEN:
            final.append(p)
        else:
            for i in range(0, len(p), SAFE_SPLIT):
                final.append(p[i:i + SAFE_SPLIT])
    return final


# Кнопка в меню: callback_data="free_chatgpt" уже есть
@chat_router.callback_query(F.data == "free_chatgpt")
async def free_chat_start(call: CallbackQuery, state: FSMContext, config: Config):
    client = await select_client(call.message.chat.id)
    today = date.today()
    client.ensure_free_chat_quota(today)
    client.save()
    remaining = client.free_chat_daily_limit - client.free_chat_used_today
    await state.set_state(ChatStates.free_chat_question)
    await call.message.edit_text(
        f"Бесплатный ChatGPT.\nОсталось запросов сегодня: {remaining} из {client.free_chat_daily_limit}.\n"
        f"Отправьте вопрос одним сообщением.",
        reply_markup=await back_to_menu_kb()
    )


@chat_router.message(ChatStates.free_chat_question)
async def free_chat_ask(message: Message, state: FSMContext, config: Config):
    question = message.text.strip() if message.text else ""
    if not question:
        await message.reply("Пустой вопрос. Напишите текст.")
        return
    client = await select_client(message.chat.id)
    today = date.today()
    client.ensure_free_chat_quota(today)
    if not client.has_free_chat_quota():
        remaining = 0
        await message.reply(
            f"Лимит бесплатных запросов исчерпан. Сегодня осталось: {remaining}. Повторите завтра.",
            reply_markup=await back_to_menu_kb()
        )
        return

    thinking_msg = await message.reply("Думаю над ответом ...")

    try:
        answer = await config.tg_bot.gpt_svc.ask(question=question)
    except Exception as e:
        try:
            await thinking_msg.edit_text(f"Ошибка: {e}")
        except:
            await message.reply(f"Ошибка: {e}")
        return

    # Учет квоты
    client.inc_free_chat_usage()
    client.save()

    chunks = split_long(answer)
    try:
        await thinking_msg.edit_text(chunks[0])
    except:
        await message.reply(chunks[0])
    for extra in chunks[1:]:
        await message.answer(extra)

    remaining = client.free_chat_daily_limit - client.free_chat_used_today
    await message.answer(
        f"Осталось бесплатных запросов сегодня: {remaining}. Можете задать следующий вопрос.",
        reply_markup=await back_to_menu_kb()
    )
