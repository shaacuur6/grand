from django.db import migrations


DEFAULT_CATEGORIES = [
    "Payroll",
    "Utilities",
    "Rent",
    "Maintenance",
    "Supplies",
    "Transport",
    "Marketing",
    "Bank Charges",
    "Taxes & Licenses",
    "Other Expenses",
]


def create_categories(apps, schema_editor):
    ExpenseCategory = apps.get_model("finance", "ExpenseCategory")
    for name in DEFAULT_CATEGORIES:
        ExpenseCategory.objects.get_or_create(name=name, defaults={"active": True})


def remove_categories(apps, schema_editor):
    ExpenseCategory = apps.get_model("finance", "ExpenseCategory")
    ExpenseCategory.objects.filter(name__in=DEFAULT_CATEGORIES).delete()


class Migration(migrations.Migration):
    dependencies = [("finance", "0001_initial")]

    operations = [migrations.RunPython(create_categories, remove_categories)]
