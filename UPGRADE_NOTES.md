# Hotel Restaurant HMS - Booking/Billing Upgrade

## Important booking rules

1. **Room transfers use `RoomStay`**. Each room occupied by a guest is recorded as a separate stay segment with its own locked nightly rate.
2. A stay segment uses **start date inclusive / end date exclusive**. Example: Room 101 from Sep 1 to Sep 3 = 2 nights. If the guest moves to Room 205 on Sep 3, Room 205 starts Sep 3. The transfer day is therefore not charged twice.
3. Historical rates are preserved. Changing a Room's current price does not rewrite old room-stay charges.
4. Changing AC on an active booking is treated as a rate change from the current hotel day forward; previous nights keep their old rate.
5. **Hotel checkout cutoff is 1:00 PM local time**. Checkout after 1:00 PM adds one additional room night unless the staff marks **Late checkout approved / notice received**.
6. Checkout records the actual checkout timestamp and the late-checkout charge.
7. The final invoice is recalculated at checkout from room stays + services + restaurant orders - discount.

## New functionality

- Separate Room Transfer form and URL.
- Room-stay ledger and room-revenue reports.
- Improved reservation/guest-history filtering.
- Search by guest name, phone, or room number.
- Checkout-from / checkout-to filters.
- Room status: Available, Occupied, Cleaning, Maintenance, Out of Order.
- Safer Decimal-based payment validation.
- Fixed hard-coded revenue date logic.
- Fixed maintenance-report dependency on a missing Room.status field.
- Added Django migration `hotel/0002_roomstay_booking_actual_times.py`.

## Upgrade steps

Back up the database first, then from the project directory:

```bash
python manage.py migrate
python manage.py check
python manage.py test hotel
```

If your environment is a virtual environment, activate it before running these commands.

## Recommended operational workflow

**New guest:** New Booking -> Check In -> services/restaurant -> Transfer Room if needed -> Checkout -> Payment.

**Room transfer:** Use the transfer button on the active booking. Do not change the room through the normal booking edit form. This keeps the historical room/rate ledger correct.

**Checkout:** Review the room-stay ledger and late-checkout warning. If approval/notice exists, tick the approval box; otherwise the system adds one extra room night after 1:00 PM.

## Compatibility note

The uploaded project currently contains a `requirements.txt` declaring Django 6.1.1 while the project source comments describe Django 5.2. Before production deployment, keep one Django version consistently installed in the virtual environment and test the complete project after `migrate` and `check`.
