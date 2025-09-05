import asyncio
import uuid
import json
from typing import Any, Optional

from yookassa import Configuration, Payment
from yookassa.domain.exceptions import ApiError


class YandexKassaService:
    """
    Обёртка над официальной SDK YooKassa.
    Использует поток для выполнения синхронных вызовов внутри async-кода.
    """

    def __init__(self, shop_id: str, api_key: str):
        self._shop_id = shop_id
        self._api_key = api_key
        # Конфигурация глобальна для SDK; при необходимости можно перенастраивать перед каждым вызовом.
        Configuration.configure(account_id=self._shop_id, secret_key=self._api_key)

    async def create_payment(self, amount_rub: float, description: str, return_url: str) -> dict[str, Any]:
        """
        Создание платежа. Возвращает dict с полями, аналогичными прежней реализации.
        """
        payload = {
            "amount": {"value": f"{amount_rub:.2f}", "currency": "RUB"},
            "capture": True,
            "confirmation": {
                "type": "redirect",
                "return_url": return_url
            },
            "description": description,
        }
        idem_key = str(uuid.uuid4())

        def _do():
            try:
                payment = Payment.create(payload, idem_key)
                data = json.loads(payment.json())
                # Унификация структуры
                return {
                    "id": data.get("id"),
                    "status": data.get("status"),
                    "amount": data.get("amount"),
                    "confirmation": data.get("confirmation"),
                    "description": data.get("description"),
                    "raw": data,
                }
            except ApiError as e:
                raise RuntimeError(f"YooKassa error: {e}")

        return await asyncio.to_thread(_do)

    async def get_payment(self, payment_id: str) -> Optional[dict]:
        """
        Получение статуса платежа по ID.
        """

        def _do():
            try:
                payment = Payment.find_one(payment_id)
                return json.loads(payment.json())
            except ApiError:
                return None

        return await asyncio.to_thread(_do)
