#from datetime import timezone
from django.utils import timezone
from django.db import models
from django.db.models import Sum, F
from hotel.models import Booking
from django.contrib.auth.models import User


class FoodCategory(models.Model):
    name = models.CharField(max_length=100)
    created = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    def __str__(self):
        return self.name

class FoodItem(models.Model):
    category = models.ForeignKey(FoodCategory, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    image = models.ImageField(upload_to="food_images/", blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    def __str__(self):
        return self.name
    




class Employee(models.Model):

    employee_no = models.CharField(max_length=20,unique=True)

    full_name = models.CharField( max_length=200)

    phone = models.CharField(max_length=20,blank=True,null=True)

    position = models.CharField(max_length=100,blank=True,null=True)

    active = models.BooleanField(default=True)

    def __str__(self):
        return self.full_name



class Order(models.Model):
    table_number = models.IntegerField(blank=True, null=True)
    employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True)
    booking = models.ForeignKey(
        Booking,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="orders"
    )

    waiter = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    #created = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    created_by = models.ForeignKey(
            User,
            on_delete=models.SET_NULL,
            null=True,
            blank=True,
            related_name="order_created_by"
        )
   
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0) 
    #def total_amount(self):
     #   return sum(item.total_price() for item in self.items.all())

    def update_total(self):
        total = self.items.aggregate(
            total=Sum(F("quantity") * F("food__price"))
        )["total"] or 0
        print(total)
        self.total_amount = total
        self.save()

    

    def __str__(self):
        return f"Order {self.id}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE,related_name="items")
    food = models.ForeignKey(FoodItem, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    description = models.CharField(
        max_length=200,
        blank=True,
        null=True)

    def total_price(self):
        return self.quantity * self.food.price




