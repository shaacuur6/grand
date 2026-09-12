from django.db import migrations, models
import django.db.models.deletion


def sync_room_status(apps, schema_editor):
    Room = apps.get_model("hotel", "Room")
    for room in Room.objects.all():
        room.status = "available" if room.is_available else "occupied"
        room.save(update_fields=["status"])


def create_initial_room_stays(apps, schema_editor):
    Booking = apps.get_model("hotel", "Booking")
    RoomStay = apps.get_model("hotel", "RoomStay")
    for booking in Booking.objects.all().iterator():
        if not booking.room_id:
            continue
        if RoomStay.objects.filter(booking_id=booking.pk).exists():
            continue
        RoomStay.objects.create(
            booking_id=booking.pk,
            room_id=booking.room_id,
            start_date=booking.check_in,
            end_date=booking.check_out,
            rate=booking.room_price or 0,
            with_ac=booking.with_ac,
            note="Migrated from existing booking",
        )


class Migration(migrations.Migration):
    dependencies = [("hotel", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="room",
            name="status",
            field=models.CharField(
                choices=[
                    ("available", "Available"),
                    ("occupied", "Occupied"),
                    ("cleaning", "Cleaning"),
                    ("maintenance", "Maintenance"),
                    ("out_of_order", "Out of Order"),
                ],
                default="available",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="booking",
            name="actual_check_in_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="booking",
            name="actual_check_out_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="booking",
            name="late_checkout_approved",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="booking",
            name="late_checkout_charge",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=8),
        ),
        migrations.CreateModel(
            name="RoomStay",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("start_date", models.DateField()),
                ("end_date", models.DateField(blank=True, null=True)),
                ("rate", models.DecimalField(decimal_places=2, max_digits=10)),
                ("with_ac", models.BooleanField(default=False)),
                ("note", models.CharField(blank=True, max_length=255)),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("booking", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="room_stays", to="hotel.booking")),
                ("room", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="booking_stays", to="hotel.room")),
            ],
            options={"ordering": ["start_date", "id"]},
        ),
        migrations.AddConstraint(
            model_name="roomstay",
            constraint=models.UniqueConstraint(fields=("booking", "start_date"), name="unique_booking_roomstay_start"),
        ),
        migrations.RunPython(sync_room_status, migrations.RunPython.noop),
        migrations.RunPython(create_initial_room_stays, migrations.RunPython.noop),
    ]
