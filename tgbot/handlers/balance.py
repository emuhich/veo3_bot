from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from aiogram import Router, F
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, LabeledPrice

from admin_panel.telebot.models import Payment, Client
from tgbot.config import Config
from tgbot.keyboards.inline import topup_amount_kb, topup_method_kb, topup_check_kb
from tgbot.misc.states import BalanceStates
from tgbot.models.db_commands import select_client, AsyncDatabaseOperations
from tgbot.services.cryptobot_service import CryptoBotService
from tgbot.services.yookassa_service import YandexKassaService

balance_router = Router()

COIN_RATE_RUB = 80  # 1 монета = 80 руб
USDT_RATE_RUB = 95  # пример курса (введите обновление из внешнего источника)
MIN_CUSTOM_COINS = 1
MAX_CUSTOM_COINS = 1000


async def _create_payment(client: Client, coins: int) -> Payment:
    amount_rub = Decimal(coins * COIN_RATE_RUB)
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
        f"Вы выбрали {coins} мон.\nК оплате: {coins * COIN_RATE_RUB} ₽.\nВыберите способ оплаты:",
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
        f"Вы выбрали {coins} мон.\nИтого: {coins * COIN_RATE_RUB} ₽.\nМетод?",
        reply_markup=await topup_method_kb(payment.id)
    )


async def _load_payment(payment_id: int) -> Optional[Payment]:
    try:
        return await AsyncDatabaseOperations.get_object_or_none(Payment, id=payment_id)
    except Exception:
        return None


@balance_router.callback_query(BalanceStates.waiting_method, F.data.startswith("topup_mtd_"))
async def topup_method_select(call: CallbackQuery, state: FSMContext, config: Config):
    parts = call.data.split("_")
    method_code = parts[2]
    payment_id = int(parts[3])
    payment = await _load_payment(payment_id)
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
                return_url="https://t.me/your_bot_username"
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
        # Переводим рубли в USDT через примерный курс
        usdt_amount = float(payment.amount_rub) / USDT_RATE_RUB
        usdt_amount = round(usdt_amount, 2)
        try:
            resp = await cb.create_invoice_usdt(usdt_amount, desc)
            payment.method = "cryptobot"
            payment.external_id = str(resp["invoice_id"])
            payment.check_url = resp["pay_url"]
            payment.save()
        except Exception as e:
            await call.message.edit_text(f"Ошибка создания CryptoBot инвойса: {e}")
            return
        await state.set_state(BalanceStates.waiting_payment)
        await call.message.edit_text(
            f"Оплатите (USDT ≈ {usdt_amount}).\nСсылка:\n{payment.check_url}\nДалее нажмите 'Проверить оплату'.",
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
                provider_token="",  # для Stars оставить пустым
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
async def topup_check(call: CallbackQuery, state: FSMContext, config: Config):
    payment_id = int(call.data.rsplit("_", 1)[-1])
    payment = await _load_payment(payment_id)
    if not payment:
        await call.message.edit_text("Платёж не найден.")
        return
    if payment.status == "paid":
        await call.message.edit_text("Уже оплачен.")
        return

    client = payment.client

    # Проверка YooKassa
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
