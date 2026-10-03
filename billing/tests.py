from datetime import date
from decimal import Decimal
from django.test import TestCase
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
