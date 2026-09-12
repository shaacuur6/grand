from django.db import models
from decimal import Decimal
from django.db.models import Sum, F
from hotel.models import Booking
from django.contrib.auth.models import User

from restaurant.models import Order 
from hotel.models import Service

# Create your models here.
class Invoice(models.Model):

    booking = models.OneToOneField(Booking,on_delete=models.CASCADE,related_name="invoice")

    restaurant_total = models.DecimalField(max_digits=8,decimal_places=2,default=0)

    room_total = models.DecimalField(max_digits=8,decimal_places=2,default=0)

    service_total = models.DecimalField(max_digits=10, decimal_places=2,default=0)

    discount = models.DecimalField(max_digits=5,decimal_places=2,default=0)

    total = models.DecimalField(max_digits=10,decimal_places=2)


    created = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    created_by = models.ForeignKey(
            User,
            on_delete=models.SET_NULL,
            null=True,
            blank=True
        )


    def save(self, *args, **kwargs):
        self.total = max(Decimal("0.00"), self.room_total + self.restaurant_total + self.service_total - self.discount)
        super().save(*args, **kwargs)

    @property
    def paid_total(self):
        return self.payment_set.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    @property
    def balance(self):
        return max(Decimal("0.00"), self.total - self.paid_total)

    @property
    def payment_status(self):
        if self.paid_total <= 0:
            return "unpaid"
        if self.balance <= 0:
            return "paid"
        return "partial"



    def update_invoice_restaurant_total(self, booking):
        from .services import sync_invoice
        return sync_invoice(booking)



class PaymentAllocation(models.Model):

    ALLOCATION_TYPES = (

        ("restaurant", "Restaurant"),
        ("service", "Service"),
        ("room", "Room"),

    )

    payment = models.ForeignKey(
        "Payment",
        on_delete=models.CASCADE,
        related_name="allocations"
    )

    allocation_type = models.CharField(
        max_length=20,
        choices=ALLOCATION_TYPES
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    def __str__(self):

        return f"{self.payment} - {self.allocation_type} - {self.amount}"
    



class RestaurantPaymentAllocation(models.Model):

    payment = models.ForeignKey(
        "Payment",
        on_delete=models.CASCADE
    )

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )



class ServicePaymentAllocation(models.Model):

    payment = models.ForeignKey(
        "Payment",
        on_delete=models.CASCADE
    )

    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )



class RoomPaymentAllocation(models.Model):

    payment = models.ForeignKey(
        "Payment",
        on_delete=models.CASCADE
    )

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )




class Payment(models.Model):

    invoice = models.ForeignKey(Invoice,on_delete=models.CASCADE)
#    order_ref = models.ForeignKey(Order,on_delete=models.CASCADE, blank=True, null=True)
 #   service_ref = models.ForeignKey(Service, on_delete=models.CASCADE, blank=True, null=True)
  #  booking_ref = models.ForeignKey(Booking, on_delete=models.CASCADE, blank=True, null=True)
    amount = models.DecimalField(max_digits=10,decimal_places=2)

    payment_method = models.CharField(max_length=50)
    #charge_type = models.CharField(max_length=20)

    #discount = models.DecimalField(max_digits=5,decimal_places=2,default=0)

    created = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    received_by = models.ForeignKey(
            User,
            on_delete=models.SET_NULL,
            null=True,
            blank=True
        )