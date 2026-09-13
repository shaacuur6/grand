from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, Q, Sum
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from accounts.constants import MANAGEMENT_ROLES
from accounts.mixins import RoleRequiredMixin
from .forms import InventoryItemForm, PurchaseForm, PurchaseItemFormSet, SupplierForm
from .models import InventoryItem, Purchase, PurchaseItem, Supplier


def purchase_total(purchase):
    return sum((row.quantity * row.unit_price for row in purchase.items.all()), Decimal("0.00"))


def stock_map(purchase):
    data = {}
    for row in purchase.items.all():
        data[row.item_id] = data.get(row.item_id, Decimal("0.00")) + row.quantity
    return data


def apply_stock_delta(delta):
    """Apply a purchase quantity delta to inventory atomically."""
    for item_id, quantity in delta.items():
        item = InventoryItem.objects.select_for_update().get(pk=item_id)
        new_stock = item.current_stock + quantity
        if new_stock < 0:
            raise ValidationError(f"Cannot reduce {item.name} below zero stock.")
        item.current_stock = new_stock
        item.save(update_fields=["current_stock"])


class SupplierListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    allowed_roles = MANAGEMENT_ROLES
    model = Supplier; template_name = "purchases/supplier_list.html"; context_object_name = "suppliers"
    def get_queryset(self):
        qs = Supplier.objects.order_by("name")
        q = self.request.GET.get("q", "").strip()
        return qs.filter(Q(name__icontains=q) | Q(contact_person__icontains=q) | Q(phone__icontains=q)) if q else qs


class SupplierCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    allowed_roles = MANAGEMENT_ROLES
    model = Supplier; form_class = SupplierForm; template_name = "purchases/supplier_form.html"; success_url = reverse_lazy("supplier_list")
    def form_valid(self, form):
        form.instance.created_by = self.request.user; messages.success(self.request, "Supplier added successfully."); return super().form_valid(form)


class SupplierUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    allowed_roles = MANAGEMENT_ROLES
    model = Supplier; form_class = SupplierForm; template_name = "purchases/supplier_form.html"; success_url = reverse_lazy("supplier_list")


class SupplierDeleteView(LoginRequiredMixin, RoleRequiredMixin, DeleteView):
    allowed_roles = MANAGEMENT_ROLES
    model = Supplier; template_name = "purchases/supplier_confirm_delete.html"; success_url = reverse_lazy("supplier_list")


class SupplierDetailView(LoginRequiredMixin, RoleRequiredMixin, DetailView):
    allowed_roles = MANAGEMENT_ROLES
    model = Supplier; template_name = "purchases/supplier_detail.html"; context_object_name = "supplier"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["purchases"] = self.object.purchase_set.select_related("supplier").prefetch_related("items__item").order_by("-date", "-id")
        return context


class InventoryItemListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    allowed_roles = MANAGEMENT_ROLES
    model = InventoryItem; template_name = "purchases/inventoryitem_list.html"; context_object_name = "items"
    def get_queryset(self):
        qs = InventoryItem.objects.order_by("name")
        q = self.request.GET.get("q", "").strip()
        if self.request.GET.get("low") == "1": qs = qs.filter(current_stock__lte=F("reorder_level"))
        if q: qs = qs.filter(name__icontains=q)
        return qs


class InventoryItemCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    allowed_roles = MANAGEMENT_ROLES
    model = InventoryItem; form_class = InventoryItemForm; template_name = "purchases/inventoryitem_form.html"; success_url = reverse_lazy("inventoryitem_list")


class InventoryItemUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    allowed_roles = MANAGEMENT_ROLES
    model = InventoryItem; form_class = InventoryItemForm; template_name = "purchases/inventoryitem_form.html"; success_url = reverse_lazy("inventoryitem_list")


class InventoryItemDeleteView(LoginRequiredMixin, RoleRequiredMixin, DeleteView):
    allowed_roles = MANAGEMENT_ROLES
    model = InventoryItem; template_name = "purchases/inventoryitem_confirm_delete.html"; success_url = reverse_lazy("inventoryitem_list")


class PurchaseListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    allowed_roles = MANAGEMENT_ROLES
    model = Purchase; template_name = "purchases/purchase_list.html"; context_object_name = "purchases"
    def get_queryset(self):
        qs = Purchase.objects.select_related("supplier").prefetch_related("items__item").order_by("-date", "-id")
        q = self.request.GET.get("q", "").strip()
        if q: qs = qs.filter(supplier__name__icontains=q)
        return qs


class PurchaseCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    allowed_roles = MANAGEMENT_ROLES
    model = Purchase; form_class = PurchaseForm; template_name = "purchases/purchase_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["formset"] = PurchaseItemFormSet(self.request.POST or None)
        return context

    @transaction.atomic
    def form_valid(self, form):
        formset = PurchaseItemFormSet(self.request.POST)
        if not formset.is_valid():
            return self.render_to_response(self.get_context_data(form=form, formset=formset))
        purchase = form.save(commit=False); purchase.added_by = self.request.user; purchase.save()
        formset.instance = purchase; formset.save()
        delta = stock_map(purchase); apply_stock_delta(delta)
        purchase.total_amount = purchase_total(purchase); purchase.save(update_fields=["total_amount"])
        messages.success(self.request, "Purchase created and stock updated.")
        return redirect("purchase_detail", pk=purchase.pk)


class PurchaseDetailView(LoginRequiredMixin, RoleRequiredMixin, DetailView):
    allowed_roles = MANAGEMENT_ROLES
    model = Purchase; template_name = "purchases/purchase_detail.html"; context_object_name = "purchase"
    def get_queryset(self): return Purchase.objects.select_related("supplier", "added_by").prefetch_related("items__item")


class PurchaseUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    allowed_roles = MANAGEMENT_ROLES
    model = Purchase; form_class = PurchaseForm; template_name = "purchases/purchase_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs); context["formset"] = PurchaseItemFormSet(self.request.POST or None, instance=self.object); return context

    @transaction.atomic
    def form_valid(self, form):
        formset = PurchaseItemFormSet(self.request.POST, instance=self.object)
        if not formset.is_valid(): return self.render_to_response(self.get_context_data(form=form, formset=formset))
        old = stock_map(self.object)
        purchase = form.save(); formset.instance = purchase; formset.save()
        new = stock_map(purchase)
        delta = dict(old)
        for item_id, qty in new.items(): delta[item_id] = delta.get(item_id, Decimal("0.00")) - qty
        delta = {k: -v for k, v in delta.items()}
        apply_stock_delta(delta)
        purchase.total_amount = purchase_total(purchase); purchase.save(update_fields=["total_amount"])
        messages.success(self.request, "Purchase updated and stock reconciled.")
        return redirect("purchase_detail", pk=purchase.pk)


class PurchaseDeleteView(LoginRequiredMixin, RoleRequiredMixin, DeleteView):
    allowed_roles = MANAGEMENT_ROLES
    model = Purchase; template_name = "purchases/purchase_confirm_delete.html"
    def get_success_url(self): return reverse_lazy("purchase_list")

    @transaction.atomic
    def form_valid(self, form):
        delta = {item_id: -qty for item_id, qty in stock_map(self.object).items()}
        apply_stock_delta(delta)
        messages.success(self.request, "Purchase deleted and stock reversed.")
        return super().form_valid(form)
