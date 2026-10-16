from dataclasses import dataclass, field

from minibill.money import to_money


@dataclass
class LineItem:
    name: str
    unit_price: float
    quantity: int = 1

    def __post_init__(self):
        self.unit_price = to_money(self.unit_price)
        if self.quantity < 1:
            raise ValueError("quantity must be at least 1")


@dataclass
class Invoice:
    items: list[LineItem] = field(default_factory=list)
    discount_rate: float = 0.0
    tax_rate: float = 0.20

    def __post_init__(self):
        self.discount_rate = to_money(self.discount_rate)
        self.tax_rate = to_money(self.tax_rate)
