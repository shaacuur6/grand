from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("hotel", "0003_booking_ledger_cleanup"),
        ("billing", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="invoice",
            name="booking",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="invoice",
                to="hotel.booking",
            ),
        ),
    ]
