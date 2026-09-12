from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
# Create your models here.

class Supplier(models.Model):
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=200, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    def __str__(self):
        return self.name


class Purchase(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    date = models.DateField(default=timezone.now)
    created = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    added_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    def __str__(self):
        return f"Purchase {self.id} - {self.supplier.name}"



class InventoryItem(models.Model):
    name = models.CharField(max_length=200)
    unit = models.CharField(max_length=20)      # Kg, Liter, Piece, Box
    current_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reorder_level = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return self.name



class PurchaseItem(models.Model):

    purchase = models.ForeignKey(
        Purchase,
        on_delete=models.CASCADE,
        related_name="items"
    )

    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.CASCADE
    )

    quantity = models.DecimalField(max_digits=10, decimal_places=2)

    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    description = models.CharField(
        max_length=200,
        blank=True,
        null=True
    )

    @property
    def total_price(self):
        return self.quantity * self.unit_price

