from .models import Booking, RoomStay
from billing.services import sync_invoice


def ensure_room_stay(booking):
    if booking.room_stays.exists():
        return booking.room_stays.filter(end_date__isnull=True).last() or booking.room_stays.last()
    return RoomStay.objects.create(
        booking=booking,
        room=booking.room,
        start_date=booking.check_in,
        rate=booking.room_price or booking.room.rate_for(booking.with_ac),
        with_ac=booking.with_ac,
        note="Initial room",
    )


def update_invoice_totals(invoice):
    return sync_invoice(invoice.booking)
