from decimal import Decimal
from django.test import TestCase
from .models import Expense, ExpenseCategory

class ExpenseModelTests(TestCase):
    def test_expense_creation(self):
        category = ExpenseCategory.objects.create(name='Utilities')
        expense = Expense.objects.create(category=category, description='Electricity', amount=Decimal('125.50'))
        self.assertEqual(expense.amount_decimal, Decimal('125.50'))
