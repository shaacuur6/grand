from decimal import Decimal
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from datetime import date, datetime

from hotel.models import Booking, Service
from restaurant.models import Order
from .models import Invoice, Payment

ZERO = Decimal("0.00")


def get_booking_totals(booking, as_of=None, include_checkout_night=False):
    """Single source of truth for the financial summary shown by Booking/Invoice."""
    as_of = as_of or timezone.localdate()
    # Reports may pass an HTML/query-string date (YYYY-MM-DD). Normalize it
    # here so all callers can safely compare it with model DateField values.
    if isinstance(as_of, datetime):
        as_of = as_of.date()
    elif isinstance(as_of, str):
        try:
            as_of = date.fromisoformat(as_of)
        except ValueError:
            as_of = timezone.localdate()

    room_total = ZERO
    stays = list(booking.room_stays.select_related("room").order_by("start_date", "id"))
    if stays:
        for stay in stays:
            # An open stay earns one room night on the current hotel date.
            # Without this minimum, a booking/check-in created today has
            # (today - today) == 0 nights and therefore shows a zero balance
            # until the calendar advances to tomorrow.
            if stay.end_date:
                # A same-day checked-in/checked-out stay is one billable hotel
                # night.  For multi-day stays the checkout date remains
                # exclusive (e.g. Sep 16 -> Sep 28 = 12 nights).
                nights = (stay.end_date - stay.start_date).days
                if nights == 0 and stay.end_date <= as_of:
                    nights = 1
                nights = max(nights, 0)
            elif stay.start_date <= as_of:
                nights = max((as_of - stay.start_date).days, 1)
            else:
                nights = 0
            room_total += Decimal(nights) * stay.rate
        if include_checkout_night and booking.status == "checked_in" and room_total == ZERO:
            active = next((s for s in reversed(stays) if s.end_date is None), stays[-1])
            room_total += active.rate
        if booking.status == "checked_out" and booking.late_checkout_approved:
            room_total += Decimal(booking.late_checkout_charge or ZERO)
    else:
        rate = booking.room_price or booking.room.rate_for(booking.with_ac)
        if booking.check_in <= as_of:
            nights = max((as_of - booking.check_in).days, 1)
        else:
            nights = 0
        if include_checkout_night:
            nights = max(nights, 1)
        room_total = Decimal(nights) * rate

    restaurant_total = Order.objects.filter(booking=booking).aggregate(
        total=Sum("total_amount")
    )["total"] or ZERO

    service_total = Service.objects.filter(booking=booking).aggregate(
        total=Sum("total_amount")
    )["total"] or ZERO

    return {
        "room_total": room_total,
        "restaurant_total": restaurant_total,
        "service_total": service_total,
    }


def sync_invoice(booking, *, as_of=None, include_checkout_night=False, rebuild_payment_allocations=True):
    """Create/update the booking invoice without changing its discount or payments."""
    totals = get_booking_totals(
        booking,
        as_of=as_of,
        include_checkout_night=include_checkout_night,
    )
    invoice, _ = Invoice.objects.get_or_create(
        booking=booking,
        defaults={"created_by": booking.created_by},
    )
    invoice.room_total = totals["room_total"]
    invoice.restaurant_total = totals["restaurant_total"]
    invoice.service_total = totals["service_total"]
    invoice.total = max(
        ZERO,
        invoice.room_total
        + invoice.restaurant_total
        + invoice.service_total
        - (invoice.discount or ZERO),
    )
    invoice.save(update_fields=[
        "room_total", "restaurant_total", "service_total", "total"
    ])
    if rebuild_payment_allocations:
        from .utils import rebuild_allocations
        rebuild_allocations(invoice)
    return invoice


def get_paid_total(invoice):
    return Payment.objects.filter(invoice=invoice).aggregate(
        total=Sum("amount")
    )["total"] or ZERO


def get_financial_summary(booking, *, as_of=None, include_checkout_night=False):
    invoice = Invoice.objects.filter(booking=booking).first()
    totals = get_booking_totals(
        booking,
        as_of=as_of,
        include_checkout_night=include_checkout_night,
    )
    discount = invoice.discount if invoice else ZERO
    grand_total = max(
        ZERO,
        totals["room_total"] + totals["restaurant_total"] + totals["service_total"] - discount,
    )
    paid = get_paid_total(invoice) if invoice else ZERO
    return {
        **totals,
        "discount": discount,
        "grand_total": grand_total,
        "paid_total": paid,
        "balance": grand_total - paid,
        "invoice": invoice,
    }
