import math


class StarsPaymentService:

    def __init__(self, star_rub: float):
        self.STAR_RUB = star_rub

    def rub_to_stars(self, amount_rub: float) -> int:
        return int(math.ceil(amount_rub / self.STAR_RUB))
