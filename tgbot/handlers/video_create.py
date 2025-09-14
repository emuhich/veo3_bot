import uuid
from io import BytesIO
from pathlib import Path
from typing import Union

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from loguru import logger

from admin_panel.telebot.models import Client, VideoGeneration
from tgbot.config import Config
from tgbot.keyboards.inline import video_format_kb, side_orientation_kb, back_to_menu_kb, wait_photo_kb, video_count_kb, \
    back_to_choice_format_kb, back_to_side_kb
from tgbot.misc.states import States
from tgbot.models.db_commands import AsyncDatabaseOperations, select_client
from admin_panel.config import config as main_config

video_router = Router()


@video_router.callback_query(F.data == "generate_video")
async def start_generate_video(call: CallbackQuery):
    await call.answer(сache_time=1)
    text = (
        "💡 Fast version — быстро и дёшево (до 5 сек, без озвучки).\n\n"
        "🚀 Ultra version — максимум качества, до 8 сек, улучшенная озвучка.\n\n"
    )
    await call.message.edit_text(text=text, reply_markup=await video_format_kb())


@video_router.callback_query(F.data == "fast_version")
@video_router.callback_query(F.data == "quality_version")
async def choose_video_format(call: CallbackQuery, state: FSMContext):
    model_type = 'veo3_fast' if call.data == 'fast_version' else 'veo3'
    await state.update_data(model_type=model_type)
    text_fast = (
        "💡 Fast version — быстро и дёшево (до 5 сек, без озвучки).\n\n"
        "⚙️ Характеристики:\n"
        f"• Стоимость: {main_config.MainConfig.CONT_MONEY_PER_FAST_VERSION} монеты\n"
        "• Длительность: до 8 секунд\n"
        "• Поддержка озвучки (стандартная)\n"
        "• Загрузка фото: до 1 изображения\n"
        "• Время генерации: 3–5 минут\n"
        "• Качество: улучшенное\n\n"
        "📝 Выбор соотношения сторон: 16:9 или 9:16"
    )
    text_ultra = (
        "🚀 Ultra version — максимум качества, до 8 сек, улучшенная озвучка.\n\n"
        "Премиум-качество и улучшенная озвучка:\n"
        f"• Стоимость: {main_config.MainConfig.CONT_MONEY_PER_NORMAL_VERSION} монеты\n"
        "• Длительность: до 8 сек\n"
        "• Озвучка: улучшенная\n"
        "• Фото: 1 изображение\n"
        "• Время генерации: 5–7 мин\n"
        "📝 Выбор соотношения сторон: 16:9 или 9:16"
    )
    await call.message.edit_text(text=text_fast if call.data == 'fast_version' else text_ultra,
                                 reply_markup=await side_orientation_kb())


@video_router.callback_query(F.data == "side_16_9")
@video_router.callback_query(F.data == "side_9_16")
async def choose_side_orientation(call: CallbackQuery, state: FSMContext):
    side_orientation = '16:9' if call.data == 'side_16_9' else '9:16'
    await state.update_data(side_orientation=side_orientation)
    data = await state.get_data()
    await state.set_state(States.prompt)
    await call.message.edit_text(text="\n".join([
        f"✅ Вы выбрали формат: {'Fast Version' if data['model_type'] == 'veo3_fast' else 'Ultra Version'}",
        f"🖼 Соотношение сторон: {data['side_orientation']}",
        f"✍️ Отправьте текст (до 500 символов) или 🎤 голосовое сообщение для генерации видео.",
    ]), reply_markup=await back_to_choice_format_kb(data.get("model_type")))


@video_router.message(States.prompt, F.content_type.in_(['voice', 'text']))
async def prompt_received(message: Message, state: FSMContext, config: Config):
    data = await state.get_data()
    if message.voice:
        buf = BytesIO()
        file = await message.bot.get_file(message.voice.file_id)
        await message.bot.download(file, buf)
        buf.seek(0)
        try:
            text = await config.tg_bot.gpt_svc.transcribe_bytes(
                buf,
                filename="voice.ogg",
                language="ru"
            )
        except Exception as e:
            await message.answer(f"Ошибка распознавания: {e}")
            return
        await state.update_data(prompt=text)
        await message.answer(f"Распознанный текст:\n{text}\nТеперь отправьте фото.",
                             reply_markup=await back_to_side_kb(data.get("side_orientation")))
    else:
        if not message.text:
            await message.answer("✍️ Отправьте текст (до 500 символов) или 🎤 голосовое сообщение для генерации видео.",
                                 await back_to_choice_format_kb(data.get("model_type")))
            return
        await state.update_data(prompt=message.text[:500])
    await message.answer("✨ Отлично, текст получен!\n\n📷 Прикрепите фото (или нажмите «Пропустить»).",
                         reply_markup=await wait_photo_kb(data.get("side_orientation")))
    await state.set_state(States.photo)


@video_router.message(States.photo, F.photo)
@video_router.callback_query(States.photo, F.data == "skip_photo")
async def receive_photo(event: Union[Message, CallbackQuery], state: FSMContext):
    # Пропуск фото
    data_state = await state.get_data()
    if isinstance(event, CallbackQuery):
        await event.message.delete()
        await state.update_data(photo_bytes=None, photo_filename=None, photo_mime=None)
        await event.message.answer("✨ Сколько роликов создать для вас?",
                                   reply_markup=await video_count_kb(data_state.get("side_orientation")))
        return

    # Фото отправлено
    msg: Message = event
    file = await msg.bot.get_file(msg.photo[-1].file_id)
    buf = BytesIO()
    await msg.bot.download(file, buf)
    buf.seek(0)
    data = buf.getvalue()

    ext = Path(file.file_path).suffix.lower() if file.file_path else ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    await state.update_data(
        photo_bytes=data,
        photo_filename=filename,
        photo_mime=f"image/{ext.lstrip('.')}"
    )
    await msg.answer("✨ Сколько роликов создать для вас?",
                     reply_markup=await video_count_kb(data_state.get("side_orientation")))


@video_router.callback_query(F.data.in_(["vid_cnt_1", "vid_cnt_2", "vid_cnt_3"]))
async def choose_video_count(call: CallbackQuery, state: FSMContext, config: Config):
    count = int(call.data.rsplit("_", 1)[-1])
    await call.message.edit_text(f"Запускаю генерацию {count} видео...")
    await generate_multiple_videos(call.message, state, config, count)


async def generate_multiple_videos(message: Message, state: FSMContext, config: Config, count: int):
    data = await state.get_data()
    prompt = data.get("prompt")
    model = data.get("model_type")
    aspect = data.get("side_orientation")
    image_bytes = data.get("photo_bytes")
    image_filename = data.get("photo_filename")

    if not prompt or not model or not aspect:
        await message.answer("Недостаточно данных для генерации.", reply_markup=await back_to_menu_kb())
        await state.set_state(None)
        return

    user: Client = await select_client(message.chat.id)

    per_video_cost = main_config.MainConfig.CONT_MONEY_PER_FAST_VERSION if model == "veo3_fast" else main_config.MainConfig.CONT_MONEY_PER_NORMAL_VERSION
    total_cost = per_video_cost * count

    if user.balance < total_cost:
        need = total_cost - user.balance
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Пополнить баланс", callback_data="topup_start")],
            [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")]
        ])
        await message.answer(
            f"😔 Ой! Монет не хватает.\nНужно: {total_cost}, а у вас пока: {user.balance} (не хватает {need}).\n\n"
            f"Пополните баланс, чтобы продолжить 🚀",
            reply_markup=kb
        )
        await state.set_state(None)
        return

    # Списание монет единым блоком
    user.balance -= total_cost
    user.save(update_fields=["balance"])
    await message.answer(
        f"Списано {total_cost} монет за {count} видео (по {per_video_cost} за каждое). Текущий баланс: {user.balance}."
    )

    await state.set_state(None)

    for idx in range(count):
        progress_msg = await message.answer(f"({idx + 1}/{count}) Адаптирую промпт ...")
        logger.info(f'Prompt before adaptation: {prompt}')
        try:
            response = await config.tg_bot.veo_svc.generate_video(
                prompt_user=prompt,
                model=model,
                aspect_ratio=aspect,
                image_bytes=image_bytes,
                image_filename=image_filename,
            )
        except Exception as e:
            try:
                await progress_msg.edit_text(
                    f"({idx + 1}/{count}) Ошибка запуска задачи."
                )
            except Exception:
                pass
            # Возврат за конкретное несозданное задание
            user.refresh_from_db()
            user.balance += per_video_cost
            user.save(update_fields=["balance"])
            await message.answer(
                f"Возврат {per_video_cost} мон (не удалось создать задачу). Баланс: {user.balance}."
            )
            continue

        task_id = (response.get("data") or {}).get("taskId")
        if not task_id:
            try:
                await progress_msg.edit_text(f"({idx + 1}/{count}) Ошибка: нет taskId.")
            except Exception:
                pass
            user.refresh_from_db()
            user.balance += per_video_cost
            user.save(update_fields=["balance"])
            await message.answer(
                f"Возврат {per_video_cost} мон (нет taskId). Баланс: {user.balance}."
            )
            continue

        try:
            await progress_msg.edit_text("⌛️")
        except Exception:
            pass

        try:
            await AsyncDatabaseOperations.create_object(
                VideoGeneration,
                client=user,
                task_id=task_id,
                message_id=progress_msg.message_id,
                coins_charged=per_video_cost
            )
        except Exception:
            user.refresh_from_db()
            user.balance += per_video_cost
            user.save(update_fields=["balance"])
            try:
                await progress_msg.edit_text(
                    f"({idx + 1}/{count}) Ошибка сохранения задачи. Возврат {per_video_cost} мон."
                )
            except Exception:
                pass
            continue

    await message.answer(
        "Все задачи поставлены. Ожидайте результатов.",
        reply_markup=await back_to_menu_kb()
    )
