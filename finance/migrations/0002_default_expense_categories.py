from django.db import migrations


DEFAULT_CATEGORIES = [
    'Utilities',
    'Salaries & Wages',
    'Rent',
    'Repairs & Maintenance',
    'Cleaning & Laundry',
    'Food & Beverage Supplies',
    'Office Supplies',
    'Transportation',
    'Internet & Telephone',
    'Marketing & Advertising',
    'Bank & Payment Fees',
    'Taxes & Licenses',
    'Insurance',
    'Other Operating Expenses',
]


def create_default_categories(apps, schema_editor):
    ExpenseCategory = apps.get_model('finance', 'ExpenseCategory')
    for name in DEFAULT_CATEGORIES:
        ExpenseCategory.objects.get_or_create(name=name, defaults={'active': True})


def reverse_default_categories(apps, schema_editor):
    # Do not delete categories on rollback because users may have already
    # attached expenses to them or renamed/modified them.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('finance', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_default_categories, reverse_default_categories),
    ]
