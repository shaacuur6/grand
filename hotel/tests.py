from decimal import Decimal
from datetime import date
from django.test import TestCase
from .models import Room, Guest, Booking, RoomStay


class RoomStayBillingTests(TestCase):
    def setUp(self):
        self.room1 = Room.objects.create(number=101, room_type="single", price=50, price_with_ac=60, is_available=False, status="occupied")
        self.room2 = Room.objects.create(number=102, room_type="double", price=80, price_with_ac=90, is_available=False, status="occupied")
        self.guest = Guest.objects.create(first_name="Test", last_name="Guest", phone="000")
        self.booking = Booking.objects.create(guest=self.guest, room=self.room1, check_in=date(2026, 9, 1), status="checked_in", room_price=Decimal("50.00"))

    def test_transfer_day_is_not_double_charged(self):
        RoomStay.objects.create(booking=self.booking, room=self.room1, start_date=date(2026, 9, 1), end_date=date(2026, 9, 3), rate=Decimal("50.00"))
        RoomStay.objects.create(booking=self.booking, room=self.room2, start_date=date(2026, 9, 3), end_date=date(2026, 9, 5), rate=Decimal("80.00"))
        self.assertEqual(self.booking.room_total, Decimal("260.00"))

    def test_room_stay_preserves_historical_rate(self):
        stay = RoomStay.objects.create(booking=self.booking, room=self.room1, start_date=date(2026, 9, 1), end_date=date(2026, 9, 4), rate=Decimal("50.00"))
        self.room1.price = Decimal("100.00")
        self.room1.save()
        self.assertEqual(stay.total, Decimal("150.00"))
