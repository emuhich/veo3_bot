from typing import Union, Optional

from aiogram.enums import ContentType
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import (
    CallbackQuery,
    Message,
    InputFile,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    ForceReply,
)
from pydantic import ValidationError


async def one_message_editor(
    event: CallbackQuery | Message,
    text: Optional[str] = None,
    reply_markup: Optional[
        Union[
            InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, ForceReply
        ]
    ] = None,
    photo: Union[InputFile, str] = None,
    document: Union[InputFile, str] = None,
    video: Union[InputFile, str] = None,
    parse_mode: Optional[str] = "HTML",
    disable_web_page_preview: bool = False,
):
    """
    Этот метод служит для автоматического изменения/удаления предыдущего сообщения для того чтобы не захламлять
    чат и был вид одного сообщения. Можно отправлять Текст, Фото, Видео, Документы.

    :param event: Объект, который принимает handler, может быть CallbackQuery или Message
    :param text: Текст сообщения либо описание под медиа
    :param reply_markup: Клавиатура отправляемая с сообщением
    :param photo: Передавайте если хотите отправить фото
    :param document: Передавайте если хотите отправить документ
    :param video: Передавайте если хотите отправить видео
    :param parse_mode: Передавайте если хотите изменить parse_mode. Default = HTML
    :param disable_web_page_preview: Показывать преью сайта в сообщении или нет. Default = False
    """
    content_type = [ContentType.PHOTO, ContentType.VIDEO, ContentType.DOCUMENT]

    if (
        isinstance(event, CallbackQuery)
        and not photo
        and not video
        and not document
        and not event.message.content_type in content_type
    ):
        try:
            await event.message.edit_text(
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
                disable_web_page_preview=disable_web_page_preview,
            )
        except TelegramBadRequest:
            try:
                await event.message.delete()
            except TelegramBadRequest:
                pass
            await event.message.answer(
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
                disable_web_page_preview=disable_web_page_preview,
            )
        except ValidationError:
            try:
                await event.message.delete()
            except TelegramBadRequest:
                pass
            await event.message.answer(
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
                disable_web_page_preview=disable_web_page_preview,
            )
    else:
        if isinstance(event, CallbackQuery):
            event = event.message
        try:
            await event.delete()
        except TelegramBadRequest:
            pass
        if photo:
            await event.answer_photo(
                photo=photo,
                caption=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_web_page_preview,
            )
        elif video:
            await event.answer_video(
                video=video,
                caption=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_web_page_preview,
            )
        elif document:
            await event.answer_document(
                document=document,
                caption=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_web_page_preview,
            )
        else:
            await event.answer(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_web_page_preview,
            )
