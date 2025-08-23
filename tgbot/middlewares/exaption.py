import aiogram

from aiogram.types import BufferedInputFile
from typing import Callable, Any, Awaitable
import logging
import traceback
import os


class LogExceptionsMiddleware(aiogram.BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[
            [aiogram.types.TelegramObject, dict[str, Any]], Awaitable[Any]
        ],
        event: aiogram.types.TelegramObject,
        data: dict[str, Any],
    ):
        try:
            return await handler(event, data)
        except Exception as e:
            logger = logging.getLogger(__name__)
            tb_str = traceback.format_exc()
            logger.exception(e)
            bot: aiogram.Bot = data["bot"]
            log_channel_id = int(os.getenv("LOG_CHANNEL_ID"))
            if not log_channel_id:
                return
            tb_file = BufferedInputFile(tb_str.encode("utf-8"), "exception")
            event_file = BufferedInputFile(
                event.model_dump_json(indent=4).encode("utf-8"), "event.json"
            )
            await bot.send_document(
                chat_id=log_channel_id, document=tb_file, caption=str(e)
            )
            await bot.send_document(chat_id=log_channel_id, document=event_file)
