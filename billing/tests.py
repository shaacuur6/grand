from datetime import date
from decimal import Decimal
from django.test import TestCase
from django.db.models import Sum
from hotel.models import Room, Guest, Booking, RoomStay
from .services import get_booking_totals


class SameDayBillingTests(TestCase):
    def setUp(self):
        self.room = Room.objects.create(number=901, room_type="single", price=100, price_with_ac=120, is_available=False, status="occupied")
        self.guest = Guest.objects.create(first_name="Same", last_name="Day", phone="001")
        self.booking = Booking.objects.create(guest=self.guest, room=self.room, check_in=date(2026, 9, 28), status="checked_in", room_price=Decimal("100.00"))
        RoomStay.objects.create(booking=self.booking, room=self.room, start_date=date(2026, 9, 28), rate=Decimal("100.00"))

    def test_open_same_day_stay_has_one_night(self):
        totals = get_booking_totals(self.booking, as_of=date(2026, 9, 28))
        self.assertEqual(totals["room_total"], Decimal("100.00"))

    def test_open_stay_grows_by_one_night_per_day(self):
        totals = get_booking_totals(self.booking, as_of=date(2026, 9, 29))
        self.assertEqual(totals["room_total"], Decimal("200.00"))


class PaymentAllocationTests(TestCase):
    def setUp(self):
        from .models import Invoice, Payment, PaymentAllocation
        self.room = Room.objects.create(
            number=902,
            room_type="single",
            price=100,
            price_with_ac=120,
            is_available=False,
            status="occupied",
        )
        self.guest = Guest.objects.create(first_name="Allocation", last_name="Test", phone="002")
        self.booking = Booking.objects.create(
            guest=self.guest,
            room=self.room,
            check_in=date(2026, 9, 28),
            status="checked_in",
            room_price=Decimal("300.00"),
        )
        self.invoice = Invoice.objects.create(
            booking=self.booking,
            room_total=Decimal("300.00"),
            restaurant_total=Decimal("0.00"),
            service_total=Decimal("0.00"),
            discount=Decimal("0.00"),
            total=Decimal("300.00"),
        )
        self.Payment = Payment
        self.PaymentAllocation = PaymentAllocation

    def test_payment_allocation_populates_generic_summary(self):
        from .utils import rebuild_allocations
        payment = self.Payment.objects.create(
            invoice=self.invoice, amount=Decimal("125.00"), payment_method="cash"
        )
        rebuild_allocations(self.invoice)
        row = self.PaymentAllocation.objects.get(payment=payment, allocation_type="room")
        self.assertEqual(row.amount, Decimal("125.00"))

    def test_rebuild_reallocates_multiple_payments_in_payment_order(self):
        from .utils import rebuild_allocations
        first = self.Payment.objects.create(
            invoice=self.invoice, amount=Decimal("100.00"), payment_method="cash"
        )
        second = self.Payment.objects.create(
            invoice=self.invoice, amount=Decimal("150.00"), payment_method="card"
        )
        rebuild_allocations(self.invoice)
        self.assertEqual(
            self.PaymentAllocation.objects.filter(payment=first).aggregate(total=Sum("amount"))["total"],
            Decimal("100.00"),
        )
        self.assertEqual(
            self.PaymentAllocation.objects.filter(payment=second).aggregate(total=Sum("amount"))["total"],
            Decimal("150.00"),
        )
