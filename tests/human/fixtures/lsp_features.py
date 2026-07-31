def calculate_total(price: float, quantity: int = 1) -> float:
    """Return the total price for the requested quantity."""
    return price * quantity


total = calculate_total(3.5, 2)
print(total)
