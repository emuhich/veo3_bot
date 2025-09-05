from aiogram import Bot
from django.db import transaction
from django.utils import timezone

from admin_panel.telebot.models import VideoGeneration, Payment
from tgbot.config import Config
from tgbot.models.db_commands import AsyncDatabaseOperations
from tgbot.services.cryptobot_service import CryptoBotService
from tgbot.services.yookassa_service import YandexKassaService


async def send_user_video(config: Config, bot: Bot):
    videos_requests = await AsyncDatabaseOperations.get_objects_filter(VideoGeneration, status='in_progress')
    for request in videos_requests:
        try:
            status = await config.tg_bot.veo_svc.get_video_status(request.task_id)
        except Exception:
            continue
        if status['data']['errorCode']:
            request.status = 'failed'
            request.failed_message = status['data']['errorMessage']
            # Возврат монет за это видео
            if request.coins_charged > 0:
                client = request.client
                client.balance += request.coins_charged
                client.save(update_fields=["balance"])
                refunded = request.coins_charged
                request.coins_charged = 0
                request.save(update_fields=["status", "failed_message", "coins_charged"])
                await bot.edit_message_text(
                    chat_id=client.telegram_id,
                    message_id=request.message_id,
                    text=f"Ошибка генерации: {request.failed_message}.\nВозврат {refunded} мон. Баланс: {client.balance}"
                )
            else:
                request.save(update_fields=["status", "failed_message"])
        elif status['data']['response']:
            request.status = 'completed'
            request.result_url = status['data']['response']['resultUrls'][0]
            request.save(update_fields=["status", "result_url"])
            await bot.delete_message(chat_id=request.client.telegram_id,
                                     message_id=request.message_id)
            await bot.send_video(chat_id=request.client.telegram_id,
                                 caption=f"Видео готово! Ссылка: {request.result_url}",
                                 video=request.result_url)


async def check_pending_payments(config: Config, bot: Bot):
    pending = await AsyncDatabaseOperations.get_objects_filter(Payment, status="pending")
    yk: YandexKassaService = config.tg_bot.yookassa_svc
    cb: CryptoBotService = config.tg_bot.cryptobot_svc

    for p in pending:
        try:
            new_status = None

            if p.method == "yookassa" and p.external_id:
                info = await yk.get_payment(p.external_id)
                st = (info or {}).get("status")
                if st == "succeeded":
                    new_status = "paid"
                elif st in ("canceled", "expired"):
                    new_status = st

            elif p.method == "cryptobot" and p.external_id:
                st = await cb.get_status(int(p.external_id))
                if st == "paid":
                    new_status = "paid"
                elif st in ("expired", "canceled"):
                    new_status = st

            if not new_status:
                continue

            if new_status == "paid":
                # Атомарно: защита от двойного начисления при гонке
                with transaction.atomic():
                    p_refreshed = Payment.objects.select_for_update().get(id=p.id)
                    if p_refreshed.status != "paid":
                        p_refreshed.mark_paid(timezone.now())
                        client = p_refreshed.client
                        client.balance += p_refreshed.coins_requested
                        client.save(update_fields=["balance"])
                        await bot.send_message(
                            chat_id=client.telegram_id,
                            text=f"✅ Баланс пополнен: +{p_refreshed.coins_requested} монет.\nТекущий баланс: {client.balance}"
                        )
            else:
                if p.status != new_status:
                    p.status = new_status
                    p.save(update_fields=["status"])

        except Exception:
            continue
