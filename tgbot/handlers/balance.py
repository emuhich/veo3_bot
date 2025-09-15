from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from aiogram import Router, F, Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, LabeledPrice

from admin_panel.telebot.models import Payment, Client
from tgbot.config import Config
from tgbot.keyboards.inline import topup_amount_kb, topup_method_kb, topup_check_kb, menu_kb
from tgbot.misc.states import BalanceStates
from tgbot.models.db_commands import select_client, AsyncDatabaseOperations
from tgbot.services.cryptobot_service import CryptoBotService
from tgbot.services.yookassa_service import YandexKassaService
from admin_panel.config import config as main_config
from tgbot.misc.utils import get_usdt_rub_rate, RateFetchError
import time

balance_router = Router()

_USDT_RATE_CACHE: dict = {"value": None, "ts": 0.0}
_USDT_RATE_TTL = 120  # сек
_FALLBACK_USDT_RATE = Decimal("95")
MIN_CUSTOM_COINS = 1
MAX_CUSTOM_COINS = 10000


async def get_cached_usdt_rate() -> Decimal:
    now = time.time()
    if (
            _USDT_RATE_CACHE["value"] is None
            or now - _USDT_RATE_CACHE["ts"] > _USDT_RATE_TTL
    ):
        try:
            rate = await get_usdt_rub_rate()
            # sanity check
            if rate <= 0:
                raise RateFetchError("non-positive rate")
            _USDT_RATE_CACHE["value"] = rate
            _USDT_RATE_CACHE["ts"] = now
        except RateFetchError:
            if _USDT_RATE_CACHE["value"] is None:
                _USDT_RATE_CACHE["value"] = _FALLBACK_USDT_RATE
    return _USDT_RATE_CACHE["value"]


async def _create_payment(client: Client, coins: int) -> Payment:
    amount_rub = Decimal(coins * main_config.MainConfig.COIN_RATE_RUB)
    payment: Payment = await AsyncDatabaseOperations.create_object(
        Payment,
        client=client,
        method="",
        status="pending",
        coins_requested=coins,
        amount_rub=amount_rub,
    )
    return payment


@balance_router.callback_query(F.data == "topup_start")
async def topup_start(call: CallbackQuery, state: FSMContext):
    user: Client = await select_client(call.message.chat.id)
    await state.set_state(BalanceStates.choose_amount)
    await call.message.edit_text(
        f"Ваш текущий баланс: {user.balance} монет\n\nВыберите количество монет для пополнения или введите своё.",
        reply_markup=await topup_amount_kb()
    )


@balance_router.callback_query(BalanceStates.choose_amount, F.data.startswith("topup_amt_"))
async def topup_choose_preset(call: CallbackQuery, state: FSMContext, config: Config):
    if call.data == "topup_amt_custom":
        await state.set_state(BalanceStates.custom_amount)
        await call.message.edit_text("Введите число монет (целое).")
        return
    coins = int(call.data.rsplit("_", 1)[-1])
    client = await select_client(call.message.chat.id)
    payment = await _create_payment(client, coins)
    await state.update_data(payment_id=payment.id)
    await state.set_state(BalanceStates.waiting_method)
    await call.message.edit_text(
        f"Вы выбрали {coins} мон.\nК оплате: {coins * main_config.MainConfig.COIN_RATE_RUB} ₽.\nВыберите способ оплаты:",
        reply_markup=await topup_method_kb(payment.id)
    )


@balance_router.message(BalanceStates.custom_amount)
async def topup_custom_amount(message: Message, state: FSMContext, config: Config):
    try:
        coins = int(message.text.strip())
        if coins < MIN_CUSTOM_COINS or coins > MAX_CUSTOM_COINS:
            raise ValueError
    except ValueError:
        await message.reply(f"Введите число от {MIN_CUSTOM_COINS} до {MAX_CUSTOM_COINS}.")
        return
    client = await select_client(message.chat.id)
    payment = await _create_payment(client, coins)
    await state.update_data(payment_id=payment.id)
    await state.set_state(BalanceStates.waiting_method)
    await message.answer(
        f"Вы выбрали {coins} мон.\nИтого: {coins * main_config.MainConfig.COIN_RATE_RUB} ₽.\nМетод?",
        reply_markup=await topup_method_kb(payment.id)
    )


async def _load_payment(payment_id: int) -> Optional[Payment]:
    try:
        return await AsyncDatabaseOperations.get_object_or_none(Payment, id=payment_id)
    except Exception:
        return None


@balance_router.callback_query(BalanceStates.waiting_method, F.data.startswith("topup_mtd_"))
async def topup_method_select(call: CallbackQuery, state: FSMContext, config: Config, bot: Bot):
    parts = call.data.split("_")
    method_code = parts[2]
    payment_id = int(parts[3])
    payment = await _load_payment(payment_id)
    me = await bot.get_me()
    return_url = f"https://t.me/{me.username}"
    if not payment or payment.status != "pending":
        await call.message.edit_text("Платёж не найден или недоступен.")
        return

    # Метод YooKassa
    if method_code == "yk":
        yk: YandexKassaService = config.tg_bot.yookassa_svc
        desc = f"Пополнение {payment.coins_requested} монет"
        try:
            resp = await yk.create_payment(
                amount_rub=float(payment.amount_rub),
                description=desc,
                return_url=return_url
            )
            payment.method = "yookassa"
            payment.external_id = resp.get("id")
            confirmation = resp.get("confirmation", {})
            payment.check_url = confirmation.get("confirmation_url")
            payment.save()
        except Exception as e:
            await call.message.edit_text(f"Ошибка создания платежа YooKassa: {e}")
            return
        await state.set_state(BalanceStates.waiting_payment)
        await call.message.edit_text(
            f"Оплатите по ссылке:\n{payment.check_url}\nПосле оплаты нажмите 'Проверить оплату'.",
            reply_markup=await topup_check_kb(payment.id)
        )
        return

    # Метод CryptoBot
    if method_code == "cb":
        cb: CryptoBotService = config.tg_bot.cryptobot_svc
        desc = f"{payment.coins_requested} coins"
        rate = await get_cached_usdt_rate()
        usdt_amount = (payment.amount_rub / rate).quantize(Decimal("0.01"))
        try:
            resp = await cb.create_invoice_usdt(float(usdt_amount), desc)
            payment.method = "cryptobot"
            payment.external_id = str(resp["invoice_id"])
            payment.check_url = resp["pay_url"]
            payment.save()
        except Exception as e:
            await call.message.edit_text(f"Ошибка создания CryptoBot инвойса: {e}")
            return
        await state.set_state(BalanceStates.waiting_payment)
        await call.message.edit_text(
            f"Оплатите (≈ {usdt_amount} USDT по курсу {rate}).\nСсылка:\n{payment.check_url}\nДалее 'Проверить оплату'.",
            reply_markup=await topup_check_kb(payment.id)
        )
        return

    # Метод Stars
    if method_code == "ts":
        stars_service = config.tg_bot.stars_svc
        stars_needed = stars_service.rub_to_stars(float(payment.amount_rub))
        payment.method = "stars"
        payment.save()

        prices = [LabeledPrice(label=f"Пополнение {payment.coins_requested} мон", amount=stars_needed)]
        try:
            await call.bot.send_invoice(
                chat_id=call.message.chat.id,
                title="Пополнение баланса",
                description=f"{payment.coins_requested} монет",
                provider_token="",
                currency="XTR",
                prices=prices,
                payload=f"stars_payment_{payment.id}",
                start_parameter="topup-stars"
            )
            await call.message.edit_text(
                f"Создан счёт в Stars: {stars_needed} ⭐.\nПосле оплаты начисление произойдёт автоматически."
            )
        except TelegramAPIError:
            await call.message.edit_text("Ошибка отправки инвойса Stars.")
        await state.clear()
        return


@balance_router.callback_query(BalanceStates.waiting_payment, F.data.startswith("topup_check_"))
async def topup_check(call: CallbackQuery, config: Config):
    payment_id = int(call.data.rsplit("_", 1)[-1])
    payment = await _load_payment(payment_id)
    if not payment:
        await call.message.edit_text("Платёж не найден.")
        return
    if payment.status == "paid":
        await call.message.edit_text("Уже оплачен.")
        return

    client = payment.client

    if payment.method == "yookassa":
        yk: YandexKassaService = config.tg_bot.yookassa_svc
        info = await yk.get_payment(payment.external_id)
        status = (info or {}).get("status")
        if status == "succeeded":
            await _apply_success(payment, client, call)
            return
        elif status in ("canceled", "expired"):
            payment.status = status
            payment.save()
            await call.message.edit_text(f"Статус платежа: {status}.")
        else:
            await call.answer("Ещё не оплачено", show_alert=True)
        return

    # Проверка CryptoBot
    if payment.method == "cryptobot":
        cb: CryptoBotService = config.tg_bot.cryptobot_svc
        st = await cb.get_status(int(payment.external_id))
        if st == "paid":
            await _apply_success(payment, client, call)
            return
        elif st in ("expired", "canceled"):
            payment.status = st
            payment.save()
            await call.message.edit_text(f"Статус платежа: {st}.")
        else:
            await call.answer("Пока не оплачено", show_alert=True)
        return


async def _apply_success(payment: Payment, client: Client, call: CallbackQuery):
    now = datetime.now(timezone.utc)
    payment.status = "paid"
    payment.completed_at = now
    payment.save()
    # Начисление монет
    client.balance += payment.coins_requested
    client.save()
    await call.message.edit_text(
        f"Оплата успешна! Начислено {payment.coins_requested} мон. Ваш баланс: {client.balance}."
    )


@balance_router.message(F.successful_payment)
async def stars_success(message: Message):
    payload = message.successful_payment.invoice_payload
    if not payload.startswith("stars_payment_"):
        return
    pid = int(payload.split("_")[-1])
    payment = await AsyncDatabaseOperations.get_object_or_none(Payment, id=pid)
    if payment.status == "paid":
        return
    client = payment.client
    payment.mark_paid(datetime.now(timezone.utc))
    client.balance += payment.coins_requested
    client.save()
    await message.answer(f"Stars оплачено! Баланс: {client.balance} (+{payment.coins_requested}).")


@balance_router.callback_query(F.data.startswith("topup_cancel_"))
async def topup_cancel(call: CallbackQuery, state: FSMContext):
    # Формат: topup_cancel_<id>
    try:
        payment_id = int(call.data.rsplit("_", 1)[-1])
    except ValueError:
        payment_id = None

    if payment_id:
        payment = await _load_payment(payment_id)
        if payment and payment.status == "pending":
            payment.status = "canceled"
            payment.save(update_fields=["status"])

    await state.clear()
    user: Client = await select_client(call.message.chat.id)
    await call.message.edit_text(
        f"Пополнение отменено. Баланс: {user.balance} мон.",
        reply_markup=await menu_kb()
    )
