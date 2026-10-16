from minibill.models import Invoice, LineItem
from minibill.money import to_cents


def line_total(item: LineItem):
    return to_cents(item.unit_price * item.quantity)


def subtotal(invoice: Invoice):
    return sum((line_total(item) for item in invoice.items), start=0.0)


def total(invoice: Invoice):
    """Subtotal, minus discount, plus VAT, rounded once at the end."""
    discounted = subtotal(invoice) * (1 - invoice.discount_rate)
    return to_cents(discounted * (1 + invoice.tax_rate))
