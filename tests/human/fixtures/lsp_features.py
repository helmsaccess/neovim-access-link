from typing import overload


@overload
def calculate_total(
    price: float, quantity: int = 1, discount: float = 0.0
) -> float: ...


@overload
def calculate_total(
    price: str, quantity: int = 1, discount: float = 0.0
) -> str: ...


def calculate_total(
    price: float | str, quantity: int = 1, discount: float = 0.0
) -> float | str:
    """Return the total price for the requested quantity and discount."""
    if isinstance(price, str):
        return price * quantity
    return price * quantity * (1.0 - discount)


def calculate_tax(price: float, rate: float = 0.19) -> float:
    """Return the tax included in a price."""
    return price * rate


def calculate_tip(price: float, rate: float = 0.15) -> float:
    """Return a suggested tip."""
    return price * rate


total = calculate_total(3.5, 2, 0.1)
print(total)
