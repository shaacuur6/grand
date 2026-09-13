from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from .models import (
    Payment,
    RestaurantPaymentAllocation,
    ServicePaymentAllocation,
    RoomPaymentAllocation,
)

ZERO = Decimal("0.00")


def _allocated(model, field_name, obj, exclude_payment=None):
    qs = model.objects.filter(**{field_name: obj})
    if exclude_payment is not None:
        qs = qs.exclude(payment=exclude_payment)
    return qs.aggregate(total=Sum("amount"))["total"] or ZERO


def allocate_payment(invoice, payment):
    """Allocate one payment to the booking's room, restaurant and services."""
    remaining = Decimal(payment.amount)
    booking = invoice.booking

    RestaurantPaymentAllocation.objects.filter(payment=payment).delete()
    ServicePaymentAllocation.objects.filter(payment=payment).delete()
    RoomPaymentAllocation.objects.filter(payment=payment).delete()

    # Room is allocated first because it is the primary hotel charge.
    room_paid = _allocated(RoomPaymentAllocation, "booking", booking, payment)
    room_due = max(Decimal(invoice.room_total) - room_paid, ZERO)
    amount = min(remaining, room_due)
    if amount > ZERO:
        RoomPaymentAllocation.objects.create(payment=payment, booking=booking, amount=amount)
        remaining -= amount

    for order in booking.orders.all().order_by("created_at", "id"):
        if remaining <= ZERO:
            break
        paid = _allocated(RestaurantPaymentAllocation, "order", order, payment)
        due = max(Decimal(order.total_amount) - paid, ZERO)
        amount = min(remaining, due)
        if amount > ZERO:
            RestaurantPaymentAllocation.objects.create(payment=payment, order=order, amount=amount)
            remaining -= amount

    for service in booking.services.all().order_by("date", "id"):
        if remaining <= ZERO:
            break
        paid = _allocated(ServicePaymentAllocation, "service", service, payment)
        due = max(Decimal(service.total_amount) - paid, ZERO)
        amount = min(remaining, due)
        if amount > ZERO:
            ServicePaymentAllocation.objects.create(payment=payment, service=service, amount=amount)
            remaining -= amount


@transaction.atomic
def rebuild_allocations(invoice):
    """Rebuild all component allocations after invoice/payment changes."""
    RestaurantPaymentAllocation.objects.filter(payment__invoice=invoice).delete()
    ServicePaymentAllocation.objects.filter(payment__invoice=invoice).delete()
    RoomPaymentAllocation.objects.filter(payment__invoice=invoice).delete()
    for payment in Payment.objects.filter(invoice=invoice).order_by("created", "id"):
        allocate_payment(invoice, payment)
