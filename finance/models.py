from decimal import Decimal
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class ExpenseCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Expense categories'

    def __str__(self):
        return self.name


class Expense(models.Model):
    PAYMENT_METHODS = (
        ('cash', 'Cash'),
        ('bank', 'Bank'),
        ('mobile', 'Mobile Money'),
        ('card', 'Card'),
        ('other', 'Other'),
    )

    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT, related_name='expenses')
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(default=timezone.localdate)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cash')
    reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-id']

    def __str__(self):
        return f'{self.date} - {self.description} - {self.amount}'

    @property
    def amount_decimal(self):
        return self.amount or Decimal('0.00')
