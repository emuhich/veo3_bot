from aiogram import Bot

from admin_panel.telebot.models import VideoGeneration
from tgbot.config import Config
from tgbot.models.db_commands import AsyncDatabaseOperations


async def send_user_video(config: Config, bot: Bot):
    videos_requests = await AsyncDatabaseOperations.get_objects_filter(VideoGeneration, status='in_progress')
    for request in videos_requests:
        try:
            status = await config.tg_bot.veo_svc.get_video_status(request.task_id)
        except Exception as e:
            continue
        if status['data']['errorCode']:
            request.status = 'failed'
            request.failed_message = status['data']['errorMessage']
            request.save()
            await bot.edit_message_text(chat_id=request.client.telegram_id,
                                        text=f'Ошибка при генерации видео: {request.failed_message}. Попробуйте снова.',
                                        message_id=request.message_id)
        elif status['data']['response']:
            request.status = 'completed'
            request.result_url = status['data']['response']['resultUrls'][0]
            request.save()
            await bot.delete_message(chat_id=request.client.telegram_id,
                                     message_id=request.message_id)
            await bot.send_video(chat_id=request.client.telegram_id,
                                 caption=f'Ваше видео готово! Ссылка: {request.result_url}',
                                 video=request.result_url)
