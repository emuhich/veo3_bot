import asyncio

from aiogram import Bot, exceptions
from loguru import logger

from tgbot.models.db_commands import get_all_malling, get_all_users


async def start_milling(bot: Bot):
    mailings = await get_all_malling()
    for mailing in mailings:
        users = await get_all_users()
        logger.info(f"Starting mailing №{mailing.pk}")
        for user in users:
            args = [user.telegram_id]
            kwargs = {}
            if mailing.media_type in ['photo', 'video', 'document']:
                args.append(mailing.file_id)
                kwargs["caption"] = mailing.text
            else:
                args.append(mailing.text)
            await send_message_mailing(bot, mailing.media_type, args, kwargs)
        mailing.is_sent = True
        mailing.save()


async def send_message_mailing(bot, media, args, kwargs) -> bool:
    send_methods = {
        "photo": bot.send_photo,
        "video": bot.send_video,
        "document": bot.send_document,
        "no_media": bot.send_message,
    }
    send_method = send_methods.get(media)
    try:
        await send_method(*args, **kwargs)
    except exceptions.TelegramForbiddenError:
        pass
    except exceptions.TelegramRetryAfter as e:
        logger.error(f"Flood limit is exceeded. Sleep {e.retry_after} seconds.")
        await asyncio.sleep(e.retry_after)
        return await send_message_mailing(bot, media, args, kwargs)
    except (exceptions.TelegramAPIError, exceptions.TelegramBadRequest):
        pass
    else:
        return True
    return False
