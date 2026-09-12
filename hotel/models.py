from decimal import Decimal
from datetime import date
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Guest(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    address = models.CharField(max_length=200, blank=True)
    created = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"



class Room(models.Model):
    ROOM_TYPES = (
        ("single", "Single"),
        ("double", "Double"),
        ("suite", "Suite"),
    )
    ROOM_STATUS = (
        ("available", "Available"),
        ("reserved", "Reserved"),
        ("occupied", "Occupied"),
        ("cleaning", "Cleaning"),
        ("maintenance", "Maintenance"),
        ("out_of_order", "Out of Order"),
    )

    number = models.IntegerField(unique=True)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    price_with_ac = models.DecimalField(max_digits=8, decimal_places=2)
    is_available = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=ROOM_STATUS, default="available")
    created = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.number}"

    def rate_for(self, with_ac=False):
        return self.price_with_ac if with_ac else self.price

    def room_is_available(self, check_date, exclude_booking=None):
        qs = Booking.objects.filter(
            room=self,
            status__in=["reserved", "checked_in"],
            check_in__lte=check_date,
        ).filter(
            models.Q(check_out__isnull=True) | models.Q(check_out__gt=check_date)
        )
        if exclude_booking:
            qs = qs.exclude(pk=exclude_booking.pk)
        return not qs.exists()

    def __str__(self):
        return f"{self.number}"


class Booking(models.Model):
    BOOKING_STATUS = (
        ("reserved", "Reserved"),
        ("checked_in", "Checked In"),
        ("checked_out", "Checked Out"),
        ("cancelled", "Cancelled"),
    )

    guest = models.ForeignKey(Guest, on_delete=models.PROTECT)
    room = models.ForeignKey(Room, on_delete=models.PROTECT)
    check_in = models.DateField()
    check_out = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, default="checked_in")
    with_ac = models.BooleanField(default=False)
    room_price = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)

    # Actual operational timestamps. They allow correct late-checkout calculation.
    actual_check_in_at = models.DateTimeField(null=True, blank=True)
    actual_check_out_at = models.DateTimeField(null=True, blank=True)
    late_checkout_approved = models.BooleanField(default=False)
    late_checkout_charge = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))

    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    updated = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="booking_updated_by"
    )

    @property
    def stays(self):
        return self.room_stays.select_related("room").order_by("start_date", "id")

    @property
    def days(self):
        """Billable room nights. Uses the room-stay ledger when available."""
        stays = list(self.stays)
        if stays:
            nights = sum(s.nights for s in stays)
            return nights if nights > 0 else 1
        end = self.check_out or timezone.now().date()
        nights = (end - self.check_in).days
        return nights if nights > 0 else 1

    @property
    def room_total(self):
        stays = list(self.stays)
        if stays:
            total = sum((s.total for s in stays), Decimal("0.00"))
            # Before checkout, the current open stay must be valued through today.
            if self.status == "checked_in":
                total = self.room_total_as_of(timezone.now().date())
            return total
        return (Decimal(self.days) * (self.room_price or Decimal("0.00")))

    def room_total_as_of(self, end_date):
        stays = list(self.stays)
        if not stays:
            return Decimal(self.days) * (self.room_price or Decimal("0.00"))
        total = Decimal("0.00")
        for stay in stays:
            stop = stay.end_date or end_date
            nights = max((stop - stay.start_date).days, 0)
            total += Decimal(nights) * stay.rate
        # A same-day stay still carries one room night at checkout.
        if total == 0 and self.status == "checked_out":
            return self.room_price or Decimal("0.00")
        return total

    @property
    def restaurant_total(self):
        from restaurant.models import Order
        return Order.objects.filter(booking=self).aggregate(
            total=models.Sum("total_amount")
        )["total"] or Decimal("0.00")

    @property
    def service_total(self):
        return sum(
            (service.total_amount for service in self.services.all()),
            Decimal("0.00"),
        )

    @property
    def total_amount(self):
        return self.room_total + self.restaurant_total + self.service_total

    def __str__(self):
        return f"{self.guest} - {self.room}"


class RoomStay(models.Model):
    """
    Immutable-ish room-rate ledger for a booking.

    start_date is inclusive; end_date is exclusive.
    Example:
      Room 101: Jun 1 -> Jun 3 = 2 nights
      Room 205: Jun 3 -> Jun 5 = 2 nights
    This prevents the transfer day from being charged twice and preserves
    the historical rate even if the Room price changes later.
    """
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="room_stays")
    room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name="booking_stays")
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    rate = models.DecimalField(max_digits=10, decimal_places=2)
    with_ac = models.BooleanField(default=False)
    note = models.CharField(max_length=255, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["start_date", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["booking", "start_date"],
                name="unique_booking_roomstay_start",
            )
        ]

    @property
    def nights(self):
        end = self.end_date or timezone.now().date()
        return max((end - self.start_date).days, 0)

    @property
    def total(self):
        return Decimal(self.nights) * self.rate

    def __str__(self):
        return f"{self.booking} / Room {self.room.number} / {self.rate}"


# Kept for compatibility with existing code/data. New billing should use RoomStay.
class Booking_History(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.PROTECT)
    check_in = models.DateField()
    check_out = models.DateField(null=True, blank=True)
    rate = models.DecimalField(max_digits=10, decimal_places=2)

from ckeditor_uploader.fields import RichTextUploadingField

class Service(models.Model):
    SERVICE_TYPE = (
        
        ("laundry", "Laundry"),
        ("room_service", "Room Service"),
        ("other", "Other"),
    )

    
    booking = models.ForeignKey(Booking, on_delete=models.PROTECT, related_name="services")
    service_type = models.CharField(max_length=20, choices=SERVICE_TYPE)
    description = RichTextUploadingField(blank=True, null=True)
    #description = HTMLField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2,default=0)
    date = models.DateField(default=timezone.now)
    created = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    added_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    updated = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_updated_by"
    )

    def __str__(self):
        return f"{self.service_type} - {self.total_amount}"