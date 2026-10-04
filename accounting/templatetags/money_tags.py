from decimal import Decimal, InvalidOperation
from django import template
from django.utils.html import format_html

register = template.Library()


@register.filter
def money(value):
    """Format monetary values consistently across Grand HMS templates."""
    if value is None or value == "":
        value = Decimal("0.00")
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return "$0.00"

    negative = amount < 0
    amount = abs(amount)
    formatted = f"{amount:,.2f}"
    return format_html("-${}", formatted) if negative else format_html("${}", formatted)
