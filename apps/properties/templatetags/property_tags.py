from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


def _decimal(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


@register.filter
def pkr(value):
    """Format a Property price in canonical PKR notation."""
    amount = _decimal(value)
    if amount is None:
        return "PKR —"
    return f"PKR {amount:,.0f}"


@register.filter
def pkr_compact(value):
    """Format large PKR values compactly for cards and narrow layouts."""
    amount = _decimal(value)
    if amount is None:
        return "PKR —"
    if amount >= 1_000_000_000:
        return f"PKR {amount / Decimal('1000000000'):.2f}B"
    if amount >= 1_000_000:
        return f"PKR {amount / Decimal('1000000'):.2f}M"
    if amount >= 1_000:
        return f"PKR {amount / Decimal('1000'):.0f}K"
    return f"PKR {amount:,.0f}"
