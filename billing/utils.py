from decimal import Decimal
from django.db import transaction
from .models import Payment, RestaurantPaymentAllocation, ServicePaymentAllocation, RoomPaymentAllocation


def allocate_payment(invoice, payment):
    """Allocate a payment against room, restaurant and services without changing payment amount."""
    remaining = Decimal(payment.amount)
    booking = invoice.booking

    # Existing allocation rows are replaced only for this payment.
    RestaurantPaymentAllocation.objects.filter(payment=payment).delete()
    ServicePaymentAllocation.objects.filter(payment=payment).delete()
    RoomPaymentAllocation.objects.filter(payment=payment).delete()

    for order in booking.orders.all():
        if remaining <= 0:
            break
        paid = RestaurantPaymentAllocation.objects.filter(order=order).exclude(payment=payment).aggregate(
            total=__import__("django").db.models.Sum("amount")
        )["total"] or Decimal("0.00")
        due = max(Decimal(order.total_amount) - paid, Decimal("0.00"))
        amount = min(remaining, due)
        if amount:
            RestaurantPaymentAllocation.objects.create(payment=payment, order=order, amount=amount)
            remaining -= amount

    for service in booking.services.all():
        if remaining <= 0:
            break
        paid = ServicePaymentAllocation.objects.filter(service=service).exclude(payment=payment).aggregate(
            total=__import__("django").db.models.Sum("amount")
        )["total"] or Decimal("0.00")
        due = max(Decimal(service.total_amount) - paid, Decimal("0.00"))
        amount = min(remaining, due)
        if amount:
            ServicePaymentAllocation.objects.create(payment=payment, service=service, amount=amount)
            remaining -= amount

    if remaining > 0:
        paid = RoomPaymentAllocation.objects.filter(booking=booking).exclude(payment=payment).aggregate(
            total=__import__("django").db.models.Sum("amount")
        )["total"] or Decimal("0.00")
        due = max(Decimal(invoice.room_total) - paid, Decimal("0.00"))
        amount = min(remaining, due)
        if amount:
            RoomPaymentAllocation.objects.create(payment=payment, booking=booking, amount=amount)


def rebuild_allocations(invoice):
    with transaction.atomic():
        RestaurantPaymentAllocation.objects.filter(payment__invoice=invoice).delete()
        ServicePaymentAllocation.objects.filter(payment__invoice=invoice).delete()
        RoomPaymentAllocation.objects.filter(payment__invoice=invoice).delete()
        for payment in Payment.objects.filter(invoice=invoice).order_by("created", "id"):
            allocate_payment(invoice, payment)
