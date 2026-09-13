import base64
import json
from decimal import Decimal, InvalidOperation
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView, View

import qrcode

from accounts.constants import MANAGEMENT_ROLES, RESTAURANT_ROLES
from accounts.mixins import RoleRequiredMixin
from billing.services import sync_invoice
from hotel.models import Booking
from .forms import EmployeeForm, FoodCategoryForm, FoodForm
from .models import Employee, FoodCategory, FoodItem, Order, OrderItem


class POSView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    allowed_roles = RESTAURANT_ROLES
    template_name = "restaurant/pos.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "categories": FoodCategory.objects.order_by("name"),
            "bookings": Booking.objects.filter(status="checked_in").select_related("guest", "room").order_by("-check_in"),
            "employees": Employee.objects.filter(active=True).order_by("full_name"),
            "foods": FoodItem.objects.select_related("category").order_by("category__name", "name"),
        })
        return context

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        table_number = request.POST.get("table_number") or None
        booking_id = request.POST.get("booking") or None
        employee_id = request.POST.get("employee") or None
        if not any([table_number, booking_id, employee_id]):
            messages.error(request, "Select a table, hotel booking, or employee before saving the order.")
            return redirect("pos")
        if booking_id:
            booking = get_object_or_404(Booking, pk=booking_id, status="checked_in")
        else:
            booking = None
        try:
            cart = json.loads(request.POST.get("cart") or "[]")
        except json.JSONDecodeError:
            messages.error(request, "The order cart is invalid.")
            return redirect("pos")
        if not cart:
            messages.error(request, "Add at least one food item.")
            return redirect("pos")

        validated_items = []
        for row in cart:
            try:
                food = FoodItem.objects.get(pk=int(row["id"]))
                qty = int(row["qty"])
            except (KeyError, TypeError, ValueError, FoodItem.DoesNotExist):
                messages.error(request, "One of the selected food items is invalid.")
                return redirect("pos")
            if qty < 1:
                messages.error(request, "Quantity must be at least 1.")
                return redirect("pos")
            validated_items.append((food, qty, (row.get("note") or "")[:200]))

        if employee_id:
            employee = get_object_or_404(Employee, pk=employee_id, active=True)
        else:
            employee = None

        order = Order.objects.create(
            table_number=int(table_number) if table_number else None,
            booking=booking,
            employee_id=int(employee_id) if employee_id else None,
            waiter=request.user, created_by=request.user,
        )
        for food, qty, note in validated_items:
            OrderItem.objects.create(order=order, food=food, quantity=qty, description=note)
        order.update_total()
        if booking:
            sync_invoice(booking)
        messages.success(request, f"Order #{order.pk} created.")
        return redirect("pos")


class ReceiptView(LoginRequiredMixin, RoleRequiredMixin, DetailView):
    model = Order
    template_name = "restaurant/receipt.html"
    allowed_roles = RESTAURANT_ROLES

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qr = qrcode.make(f"Order {self.object.id} - Total ${self.object.total_amount}")
        buffer = BytesIO(); qr.save(buffer, format="PNG")
        context["qr_code"] = base64.b64encode(buffer.getvalue()).decode()
        return context


class OrderListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    allowed_roles = MANAGEMENT_ROLES
    model = Order
    template_name = "restaurant/orders_report.html"
    context_object_name = "orders"

    def get_queryset(self):
        qs = Order.objects.select_related("waiter", "employee", "booking__guest").prefetch_related("items__food").order_by("-created_at")
        q = self.request.GET.get("q", "").strip()
        if q:
            from django.db.models import Q
            qs = qs.filter(Q(booking__guest__first_name__icontains=q) | Q(booking__guest__last_name__icontains=q) | Q(waiter__username__icontains=q))
        return qs


class OrderDetailView(LoginRequiredMixin, RoleRequiredMixin, DetailView):
    allowed_roles = RESTAURANT_ROLES
    model = Order
    template_name = "restaurant/order_detail.html"
    context_object_name = "order"


class OrderUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    allowed_roles = MANAGEMENT_ROLES
    model = Order
    template_name = "restaurant/order_update.html"

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        old_booking = self.object.booking
        table = request.POST.get("table_number") or None
        booking_id = request.POST.get("booking") or None
        employee_id = request.POST.get("employee") or None
        self.object.table_number = int(table) if table else None
        self.object.booking_id = int(booking_id) if booking_id else None
        self.object.employee_id = int(employee_id) if employee_id else None
        self.object.save(update_fields=["table_number", "booking", "employee"])
        for item in list(self.object.items.all()):
            if request.POST.get(f"delete_{item.pk}"):
                item.delete(); continue
            food_id = request.POST.get(f"food_{item.pk}")
            qty = request.POST.get(f"quantity_{item.pk}")
            if food_id and qty:
                item.food_id = int(food_id); item.quantity = max(int(qty), 1); item.description = (request.POST.get(f"note_{item.pk}") or "")[:200]; item.save()
        self.object.update_total()
        new_booking = self.object.booking
        if old_booking: sync_invoice(old_booking)
        if new_booking and new_booking != old_booking: sync_invoice(new_booking)
        messages.success(request, f"Order #{self.object.pk} updated.")
        return redirect("order_detail", pk=self.object.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"foods": FoodItem.objects.order_by("name"), "bookings": Booking.objects.filter(status="checked_in"), "employees": Employee.objects.filter(active=True)})
        return context


class OrderDeleteView(LoginRequiredMixin, RoleRequiredMixin, DeleteView):
    allowed_roles = MANAGEMENT_ROLES
    model = Order
    template_name = "restaurant/order_confirm_delete.html"

    def get_success_url(self):
        return reverse_lazy("orders_report")

    @transaction.atomic
    def form_valid(self, form):
        booking = self.object.booking
        response = super().form_valid(form)
        if booking: sync_invoice(booking)
        messages.success(self.request, "Order deleted and invoice synchronized.")
        return response


class OrderItemReportView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    allowed_roles = MANAGEMENT_ROLES
    model = OrderItem
    template_name = "restaurant/order_item_report.html"
    context_object_name = "items"

    def get_queryset(self):
        return OrderItem.objects.select_related("order", "food", "order__waiter").order_by("-order__created_at")


class FoodListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    allowed_roles = RESTAURANT_ROLES
    model = FoodItem
    template_name = "restaurant/food_list.html"
    context_object_name = "items"


class FoodCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    allowed_roles = MANAGEMENT_ROLES
    model = FoodItem; form_class = FoodForm; template_name = "restaurant/food_form.html"; success_url = reverse_lazy("food_list")
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class FoodUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    allowed_roles = MANAGEMENT_ROLES
    model = FoodItem; form_class = FoodForm; template_name = "restaurant/food_form.html"; success_url = reverse_lazy("food_list")


class FoodDeleteView(LoginRequiredMixin, RoleRequiredMixin, DeleteView):
    allowed_roles = MANAGEMENT_ROLES
    model = FoodItem; template_name = "restaurant/food_confirm_delete.html"; success_url = reverse_lazy("food_list")


class FoodCategoryListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    allowed_roles = MANAGEMENT_ROLES
    model = FoodCategory; template_name = "restaurant/category_list.html"; context_object_name = "categories"


class FoodCategoryCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    allowed_roles = MANAGEMENT_ROLES
    model = FoodCategory; form_class = FoodCategoryForm; template_name = "restaurant/category_form.html"; success_url = reverse_lazy("category_list")
    def form_valid(self, form):
        form.instance.created_by = self.request.user; return super().form_valid(form)


class FoodCategoryUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    allowed_roles = MANAGEMENT_ROLES
    model = FoodCategory; form_class = FoodCategoryForm; template_name = "restaurant/category_form.html"; success_url = reverse_lazy("category_list")


class FoodCategoryDeleteView(LoginRequiredMixin, RoleRequiredMixin, DeleteView):
    allowed_roles = MANAGEMENT_ROLES
    model = FoodCategory; template_name = "restaurant/category_confirm_delete.html"; success_url = reverse_lazy("category_list")


class EmployeeListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    allowed_roles = MANAGEMENT_ROLES
    model = Employee; template_name = "restaurant/employee_list.html"; context_object_name = "employees"
    def get_queryset(self): return Employee.objects.order_by("full_name")


class EmployeeCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    allowed_roles = MANAGEMENT_ROLES
    model = Employee; form_class = EmployeeForm; template_name = "restaurant/employee_form.html"; success_url = reverse_lazy("employee_list")


class EmployeeUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    allowed_roles = MANAGEMENT_ROLES
    model = Employee; form_class = EmployeeForm; template_name = "restaurant/employee_form.html"; success_url = reverse_lazy("employee_list")


class EmployeeDeleteView(LoginRequiredMixin, RoleRequiredMixin, DeleteView):
    allowed_roles = MANAGEMENT_ROLES
    model = Employee; template_name = "restaurant/employee_confirm_delete.html"; success_url = reverse_lazy("employee_list")
