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
