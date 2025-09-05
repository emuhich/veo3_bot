import math


class StarsPaymentService:
    STAR_RUB = 2.8

    def rub_to_stars(self, amount_rub: float) -> int:
        return int(math.ceil(amount_rub / self.STAR_RUB))
