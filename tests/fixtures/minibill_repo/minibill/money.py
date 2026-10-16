"""Money helpers."""


def to_money(value) -> float:
    """Parse a user-supplied amount ("12.50", 12) into a float."""
    return float(value)


def to_cents(amount: float) -> float:
    """Round to 2 decimals."""
    return round(amount, 2)
