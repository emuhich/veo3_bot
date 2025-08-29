import uuid
from io import BytesIO
from pathlib import Path
from typing import Union

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from admin_panel.telebot.models import Client, VideoGeneration
from bot import logger
from tgbot.config import Config
from tgbot.keyboards.inline import video_format_kb, side_orientation_kb, back_to_menu_kb, wait_photo_kb, video_count_kb
from tgbot.misc.states import States
from tgbot.models.db_commands import AsyncDatabaseOperations, select_client

video_router = Router()


@video_router.callback_query(F.data == "generate_video")
async def start_generate_video(call: CallbackQuery):
    await call.message.edit_text(text="\n".join([
        f'Выберите формат версию для генерации видео:\n'
        f'Fast Version: ',
        f'Длительность: до 8 секунд ',
        f'Поддержка озвучки (стандартная) ',
        f'Загрузка фото: до 1 изображения ',
        f'Время генерации: 3–5 минут ',
        f'Качество: улучшенное ',
        f'Стоимость: 2 монеты ',
        f'Выбор соотношения сторон: 16:9 или 9:16\n',
        f'Quality Version ',
        f'Длительность: до 8 секунд ',
        f'Поддержка озвучки (улучшенная) ',
        f'Поддержка голосовой генерации (см. ниже) ',
        f'Загрузка фото: до 1 изображения ',
        f'Время генерации: 5–7 минут ',
        f'Качество: максимальное ',
        f'Стоимость: 4 монеты ',
        f'Выбор соотношения сторон: 16:9 или 9:16',
    ]), reply_markup=await video_format_kb())


@video_router.callback_query(F.data == "fast_version")
@video_router.callback_query(F.data == "quality_version")
async def choose_video_format(call: CallbackQuery, state: FSMContext):
    model_type = 'veo3_fast' if call.data == 'fast_version' else 'veo3'
    await state.update_data(model_type=model_type)
    await call.message.edit_text(text="Выберите соотношение сторон.", reply_markup=await side_orientation_kb())


@video_router.callback_query(F.data == "side_16_9")
@video_router.callback_query(F.data == "side_9_16")
async def choose_side_orientation(call: CallbackQuery, state: FSMContext):
    side_orientation = '16:9' if call.data == 'side_16_9' else '9:16'
    await state.update_data(side_orientation=side_orientation)
    data = await state.get_data()
    await state.set_state(States.prompt)
    await call.message.edit_text(text="\n".join([
        f"Вы выбрали формат видео: {'Fast Version' if data['model_type'] == 'veo3_fast' else 'Quality Version'}",
        f"Соотношение сторон: {data['side_orientation']}",
        f"Теперь отправьте текст для генерации видео или голосовое сообщение. Максимальная длина текста 500 символов.",
    ]), reply_markup=await back_to_menu_kb())


@video_router.message(States.prompt, F.content_type.in_(['voice', 'text']))
async def prompt_received(message: Message, state: FSMContext, config: Config):
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
        await message.answer(f"Распознанный текст:\n{text}\nТеперь отправьте фото.")
    else:
        if not message.text:
            await message.answer("Отправьте текст или голосовое сообщение.")
            return
        await state.update_data(prompt=message.text[:500])

    await message.answer("Текст получен. Теперь отправьте фото.", reply_markup=await wait_photo_kb())
    await state.set_state(States.photo)


@video_router.message(States.photo, F.photo)
@video_router.callback_query(States.photo, F.data == "skip_photo")
async def receive_photo(event: Union[Message, CallbackQuery], state: FSMContext):
    # Пропуск фото
    if isinstance(event, CallbackQuery):
        await event.message.delete()
        await state.update_data(photo_bytes=None, photo_filename=None, photo_mime=None)
        await event.message.answer("Сколько видео сгенерировать?", reply_markup=await video_count_kb())
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
    await msg.answer("Сколько видео сгенерировать?", reply_markup=await video_count_kb())


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

    # Завершаем FSM (дальше только фоновые ожидания)
    await state.set_state(None)

    for idx in range(count):
        progress_msg = await message.answer(f"({idx+1}/{count}) Адаптирую промпт под запрос ...")
        try:
            response = await config.tg_bot.veo_svc.generate_video(
                prompt_user=prompt,
                model=model,
                aspect_ratio=aspect,
                image_bytes=image_bytes,
                image_filename=image_filename,
            )
        except Exception as e:
            logger.error(f"Video generation error #{idx+1}: {e}")
            try:
                await progress_msg.edit_text(
                    f"({idx+1}/{count}) Ошибка запуска генерации.",
                    reply_markup=await back_to_menu_kb()
                )
            except Exception:
                pass
            continue

        # Извлекаем taskId
        task_id = None
        resp_data = response.get("data")
        if isinstance(resp_data, dict):
            task_id = resp_data.get("taskId")

        if not task_id:
            logger.error(f"No taskId in response #{idx+1}: {response}")
            try:
                await progress_msg.edit_text(
                    f"({idx+1}/{count}) Ошибка генерации видео.",
                    reply_markup=await back_to_menu_kb()
                )
            except Exception:
                pass
            continue

        # Обновляем сообщение о запуске
        try:
            await progress_msg.edit_text(
                f"({idx+1}/{count}) Генерирую видео ... Это может занять несколько минут ..."
            )
        except Exception:
            pass

        # Создаём запись VideoGeneration (in_progress)
        try:
            user: Client = await select_client(message.chat.id)
            await AsyncDatabaseOperations.create_object(
                VideoGeneration,
                client=user,
                task_id=task_id,
                message_id=progress_msg.message_id
            )
        except Exception as e:
            logger.error(f"DB save error for video #{idx+1}: {e}")
            try:
                await progress_msg.edit_text(
                    f"({idx+1}/{count}) Ошибка сохранения задачи.",
                    reply_markup=await back_to_menu_kb()
                )
            except Exception:
                pass
            continue

    await message.answer(
        "Все задачи поставлены в очередь. Ожидайте отправки видео.",
        reply_markup=await back_to_menu_kb()
    )