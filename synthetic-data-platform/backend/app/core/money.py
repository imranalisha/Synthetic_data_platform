from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")

def quantize(value: Decimal | int | str, places: int = 2) -> Decimal:
    return Decimal(value).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)

def q2(value: Decimal | int | str) -> Decimal:
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)