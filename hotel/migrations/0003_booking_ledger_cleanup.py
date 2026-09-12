from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("hotel", "0002_roomstay_booking_actual_times"),
    ]

    operations = [
        migrations.AlterField(
            model_name="room",
            name="status",
            field=models.CharField(
                choices=[
                    ("available", "Available"),
                    ("reserved", "Reserved"),
                    ("occupied", "Occupied"),
                    ("cleaning", "Cleaning"),
                    ("maintenance", "Maintenance"),
                    ("out_of_order", "Out of Order"),
                ],
                default="available",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="booking",
            name="guest",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="hotel.guest"),
        ),
        migrations.AlterField(
            model_name="booking",
            name="room",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="hotel.room"),
        ),
        migrations.AlterField(
            model_name="service",
            name="booking",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="services", to="hotel.booking"),
        ),
    ]
