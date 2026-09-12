from decimal import Decimal
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from hotel.models import Booking, Service
from restaurant.models import Order
from .models import Invoice, Payment

ZERO = Decimal("0.00")


def get_booking_totals(booking, as_of=None, include_checkout_night=False):
    """Single source of truth for the financial summary shown by Booking/Invoice."""
    as_of = as_of or timezone.localdate()

    room_total = ZERO
    stays = list(booking.room_stays.select_related("room").order_by("start_date", "id"))
    if stays:
        for stay in stays:
            end = stay.end_date or as_of
            nights = max((end - stay.start_date).days, 0)
            room_total += Decimal(nights) * stay.rate
        if include_checkout_night and booking.status == "checked_in" and room_total == ZERO:
            active = next((s for s in reversed(stays) if s.end_date is None), stays[-1])
            room_total += active.rate
        if booking.status == "checked_out" and booking.late_checkout_approved:
            room_total += Decimal(booking.late_checkout_charge or ZERO)
    else:
        rate = booking.room_price or booking.room.rate_for(booking.with_ac)
        nights = max((as_of - booking.check_in).days, 0)
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
