from decimal import Decimal, InvalidOperation
from django import template

register = template.Library()

@register.filter
def money(value):
    """Format a monetary value with the Grand HMS currency symbol."""
    if value is None or value == "":
        return "$0.00"
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return value
    sign = "-" if amount < 0 else ""
    amount = abs(amount)
    return f"{sign}${amount:,.2f}"
