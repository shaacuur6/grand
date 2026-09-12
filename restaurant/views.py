from urllib import request

from django.views.generic import ListView,DetailView, CreateView,UpdateView,DeleteView,TemplateView,View

from accounts.mixins import RoleRequiredMixin
from restaurant.forms import FoodForm
from .models import FoodItem, Order, OrderItem, FoodCategory,Employee
from hotel.models import Room,Booking
from billing.models import Invoice
from billing.services import sync_invoice
from django.urls import reverse_lazy
from django.http import HttpResponse
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import redirect
from django.db.models import Sum, F
from django.utils.dateparse import parse_date
import json
from django.views.generic import TemplateView
import openpyxl
from reportlab.pdfgen import canvas
import qrcode
import base64
from io import BytesIO
from django.contrib.auth.mixins import LoginRequiredMixin



class ReceiptView(LoginRequiredMixin,RoleRequiredMixin,DetailView):

    model = Order
    template_name = "restaurant/receipt.html"
    allowed_roles = ["admin", "manager", "waiter", "reception"]

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        order = self.object

        # QR code data
        qr_data = f"Order {order.id} - Total ${order.total_amount}"

        qr = qrcode.make(qr_data)

        buffer = BytesIO()
        qr.save(buffer, format="PNG")

        img_str = base64.b64encode(buffer.getvalue()).decode()

        context["qr_code"] = img_str

        return context





class POSView(LoginRequiredMixin,RoleRequiredMixin,TemplateView):

    allowed_roles = ["waiter", "reception", "admin", "manager"]
    
    #model = FoodItem
    #fields = "__all__"
    template_name = "restaurant/pos.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["categories"] = FoodCategory.objects.all()
        context["bookings"] = Booking.objects.filter(status="checked_in")
        context["employees"] = Employee.objects.all()

        context["foods"] = FoodItem.objects.select_related("category").all()

        return context



    
    def post(self, request, *args, **kwargs):
        table_number = request.POST.get("table_number")
        booking_id = request.POST.get("booking")
        employee_id = request.POST.get("employee")

        order = Order.objects.create(
            table_number=int(table_number) if table_number else None,
            booking_id=int(booking_id) if booking_id else None,
            employee_id=int(employee_id) if employee_id else None,
            waiter=request.user,
            created_by=request.user
        )

        cart_data = request.POST.get("cart")

        cart = json.loads(cart_data) if cart_data else []

        for item in cart:
            food = FoodItem.objects.get(id=item["id"])

            OrderItem.objects.create(
                order=order,
                food=food,
                quantity=item["qty"],
                description=item.get("note", "")
                
            )
            #total += food.price * item["qty"]

        order.update_total()
        return redirect("pos")

class OrderUpdateView(LoginRequiredMixin,RoleRequiredMixin,UpdateView):
    model = Order
    template_name = "restaurant/order_update.html"
    fields = ["table_number", "booking","employee"]  # allow switching
    allowed_roles = ["admin", "manager"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["foods"] = FoodItem.objects.all()
        context["bookings"] = Booking.objects.filter(status="checked_in")
        context["employees"] = Employee.objects.all()
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        # ✅ store OLD booking before change
        old_booking = self.object.booking

        table_number = request.POST.get("table_number")
        booking_id = request.POST.get("booking")
        employee_id = request.POST.get("employee")

        # ✅ switch logic (only one allowed)   
        if table_number:
            self.object.table_number = int(table_number)
            self.object.booking = None
            self.object.employee = None
        elif booking_id:
            self.object.booking_id = int(booking_id)
            self.object.table_number = None
            self.object.employee = None
        elif employee_id:
            self.object.employee_id = int(employee_id)
            self.object.booking = None
            self.object.table_number = None

        self.object.save()

        # ✅ update order items (same as before)
        for item in self.object.items.all():
            food_id = request.POST.get(f"food_{item.id}")
            qty = request.POST.get(f"quantity_{item.id}")
            note = request.POST.get(f"note_{item.id}")
            delete = request.POST.get(f"delete_{item.id}")

            if delete:
                item.delete()
            else:
                item.food_id = int(food_id)
                item.quantity = int(qty)
                item.description = note
                item.save()

        # ✅ update order total
        self.object.update_total()

        # 🔥 IMPORTANT: update invoices

        new_booking = self.object.booking

        # 1. remove from OLD booking invoice
        if old_booking:
            sync_invoice(old_booking)
        if new_booking:
            sync_invoice(new_booking)
        return redirect("orders_report")



class OrderListView(LoginRequiredMixin,RoleRequiredMixin,ListView):
    allowed_roles = ["admin", "manager"]
    model = Order
    template_name = "restaurant/orders_report.html"
    context_object_name = "orders"
    ordering = ["created_at"]
    orders = Order.objects.all().prefetch_related("items")

    

class OrderDetailView(LoginRequiredMixin,RoleRequiredMixin,DetailView):
    allowed_roles = ["admin", "manager"]
    model = Order
    template_name = "restaurant/order_detail.html"
    context_object_name = "order"


class OrderItemReportView(LoginRequiredMixin,RoleRequiredMixin,ListView):
    allowed_roles = ["admin", "manager"]
    model = OrderItem
    template_name = "restaurant/order_item_report.html"
    context_object_name = "items"

    def get_queryset(self):

        return OrderItem.objects.select_related(
            "order",
            "food"
        ).order_by("-order__created_at")



class FoodListView(LoginRequiredMixin,RoleRequiredMixin,ListView):
    allowed_roles = ["admin", "manager"]
    model = FoodItem
    template_name = "restaurant/food_list.html"
    context_object_name = 'items'


class FoodCreateView(LoginRequiredMixin,RoleRequiredMixin,CreateView):
    allowed_roles = ["admin", "manager"]
    model = FoodItem
    form_class = FoodForm
    #fields = '__all__'
    template_name = "restaurant/food_form.html"
    success_url = reverse_lazy('food_list')

class FoodUpdateView(LoginRequiredMixin,RoleRequiredMixin,UpdateView):
    allowed_roles = ["admin", "manager"]
    model = FoodItem
    form_class = FoodForm
    #fields = '__all__'
    template_name = "restaurant/food_form.html"
    success_url = reverse_lazy('food_list') 


class FoodCategoryDeleteView(LoginRequiredMixin,RoleRequiredMixin,DeleteView):
    allowed_roles = ["admin", "manager"]
    model = FoodCategory
    template_name = "restaurant/category_confirm_delete.html"
    success_url = reverse_lazy('category_list')


class FoodCategoryListView(LoginRequiredMixin,RoleRequiredMixin,ListView):
    allowed_roles = ["admin", "manager"]
    model = FoodCategory
    template_name = "restaurant/category_list.html" 
    context_object_name = 'categories'


class FoodCategoryCreateView(LoginRequiredMixin,RoleRequiredMixin,CreateView):
    allowed_roles = ["admin", "manager"]
    model = FoodCategory
    fields = '__all__'
    template_name = "restaurant/category_form.html"
    success_url = reverse_lazy('category_list')

class FoodCategoryUpdateView(LoginRequiredMixin,RoleRequiredMixin,UpdateView):
    allowed_roles = ["admin", "manager"]
    model = FoodCategory
    fields = '__all__'
    template_name = "restaurant/category_form.html"
    success_url = reverse_lazy('category_list')


    
