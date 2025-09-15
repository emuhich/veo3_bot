import asyncio
from io import BytesIO

from aiogram import Bot
from aiogram.types import BufferedInputFile
from asgiref.sync import sync_to_async
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from admin_panel.telebot.forms import MailingForm
from admin_panel.telebot.models import Mailing, Client
from tgbot.config import load_config
from tgbot.misc.mailing import send_message_mailing


@login_required
def mailing(request):
    if request.method == 'POST':
        form = MailingForm(request.POST, request.FILES)
        if not form.is_valid():
            for error in form.errors.values():
                messages.error(request, error.data[0].message)
            return redirect("admin:telebot_mailing_add")

        data = form.cleaned_data
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        file_id = loop.run_until_complete(get_file_id(data.get('file')))

        if not data.get('schedule_checkbox'):
            count_send = loop.run_until_complete(
                mailing_django(data.get('media_type'), data.get('message_text'), file_id))
            messages.success(request, f"Рассылка успешно отправлена количество отправок: {count_send}")
            return redirect("admin:telebot_mailing_add")
        else:
            Mailing.objects.create(
                media_type=data['media_type'],
                text=data['message_text'],
                date_malling=data.get('schedule_datetime'),
                file_id=file_id
            )
            messages.success(request, "Рассылка успешно зарегистрирована")
    return redirect("admin:telebot_mailing_changelist")


async def get_file_id(file):
    if not file:
        return None
    file_type = file.content_type.split('/')[0]
    if isinstance(file.file, BytesIO):
        file_input = BufferedInputFile(file.file.getvalue(), filename=file.name)
    else:
        bytes_file = BytesIO(file.read())
        file_input = BufferedInputFile(bytes_file.getvalue(), filename=file.name)
    config = load_config(".env")
    bot = Bot(token=config.tg_bot.token, parse_mode='HTML')
    if file_type == 'image':
        message = await bot.send_photo(chat_id=config.tg_bot.admin_ids[0], photo=file_input)
        file_id = message.photo[-1].file_id
    elif file_type == "video":
        message = await bot.send_video(chat_id=config.tg_bot.admin_ids[0], video=file_input)
        file_id = message.video.file_id
    else:
        message = await bot.send_document(chat_id=config.tg_bot.admin_ids[0], document=file_input)
        file_id = message.document.file_id
    return file_id


async def mailing_django(media, text, file_id):
    users = await sync_to_async(Client.objects.all)()
    config = load_config(".env")
    bot = Bot(token=config.tg_bot.token, parse_mode='HTML')

    count_send = 0
    async for user in users:
        args = [user.telegram_id]
        kwargs = {}
        if media in ['photo', 'video', 'document']:
            args.append(file_id)
            kwargs["caption"] = text
        else:
            args.append(text)
        status = await send_message_mailing(bot, media, args, kwargs)
        if status:
            count_send += 1
    return count_send