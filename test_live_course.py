import asyncio
from decimal import Decimal
from typing import Optional
import aiohttp
import os

COINGECKO_USDT_RUB_URL = "https://api.coingecko.com/api/v3/simple/price?ids=tether&vs_currencies=rub"

class RateFetchError(Exception):
    pass

async def get_usdt_rub_rate(session: Optional[aiohttp.ClientSession] = None) -> Decimal:
    """
    Live курс 1 USDT в RUB через CoinGecko.
    Возвращает Decimal.
    """
    close_session = False
    if session is None:
        session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8))
        close_session = True
    try:
        async with session.get(COINGECKO_USDT_RUB_URL) as r:
            if r.status != 200:
                raise RateFetchError(f"Bad status {r.status}")
            data = await r.json()
            price = data.get("tether", {}).get("rub")
            if price is None:
                raise RateFetchError("No price in response")
            return Decimal(str(price))
    except Exception as e:
        raise RateFetchError(f"USDT rate fetch failed: {e}") from e
    finally:
        if close_session:
            await session.close()


async def get_telegram_star_rub_rate(
    session: Optional[aiohttp.ClientSession] = None,
    pack_price_rub: Optional[int] = None,
    pack_stars: Optional[int] = None,
) -> Decimal:
    """
    Оценочный курс 1 Star (XTR) в RUB.
    Прямого публичного API нет: цена зависит от площадки (iOS/Android/desktop) и локальных стоимостей.
    Логика:
      1. Берём цену пакета (pack_price_rub) и кол-во звёзд (pack_stars).
      2. Курс = pack_price_rub / pack_stars.
    Можно задать через переменные окружения:
      STARS_PACK_PRICE_RUB, STARS_PACK_AMOUNT
    Возвращает Decimal.
    """
    # Попытка взять из ENV
    if pack_price_rub is None:
        pack_price_rub_env = os.getenv("STARS_PACK_PRICE_RUB")
        if pack_price_rub_env and pack_price_rub_env.isdigit():
            pack_price_rub = int(pack_price_rub_env)
    if pack_stars is None:
        pack_stars_env = os.getenv("STARS_PACK_AMOUNT")
        if pack_stars_env and pack_stars_env.isdigit():
            pack_stars = int(pack_stars_env)

    # Fallback значения (пример: 5000 Stars за 4490 RUB — заменить на актуальные)
    if pack_price_rub is None:
        pack_price_rub = 4490
    if pack_stars is None:
        pack_stars = 5000

    if pack_price_rub <= 0 or pack_stars <= 0:
        raise RateFetchError("Invalid pack parameters for Stars")

    return (Decimal(pack_price_rub) / Decimal(pack_stars)).quantize(Decimal("0.0001"))


# Пример использования
async def demo():
    async with aiohttp.ClientSession() as s:
        usdt = await get_usdt_rub_rate(s)
        star = await get_telegram_star_rub_rate(s)
        print("USDT→RUB:", usdt)
        print("STAR→RUB:", star)

if __name__ == "__main__":
    asyncio.run(demo())