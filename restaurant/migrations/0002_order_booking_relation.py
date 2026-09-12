from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("hotel", "0003_booking_ledger_cleanup"),
        ("restaurant", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="order",
            name="booking",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="orders",
                to="hotel.booking",
            ),
        ),
    ]
