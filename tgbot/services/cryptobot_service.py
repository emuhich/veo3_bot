from aiocryptopay import AioCryptoPay, Networks
from typing import Optional


class CryptoBotService:
    def __init__(self, token: str, mainnet: bool = True):
        self._client = AioCryptoPay(
            token=token,
            network=Networks.MAIN_NET if mainnet else Networks.TEST_NET
        )

    async def create_invoice_usdt(self, amount_usdt: float, description: str) -> dict:
        invoice = await self._client.create_invoice(asset="USDT", amount=amount_usdt, description=description)
        return {
            "invoice_id": invoice.invoice_id,
            "pay_url": invoice.bot_invoice_url,
            "status": invoice.status,
        }

    async def get_status(self, invoice_id: int) -> Optional[str]:
        invoices = await self._client.get_invoices(invoice_ids=invoice_id)
        if invoices:
            return invoices[0].status
        return None
