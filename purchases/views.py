from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import (
    ListView,
    CreateView,
    UpdateView,
    DetailView,
    DeleteView,
)

from .models import (
    Supplier,
    InventoryItem,
    Purchase,
    PurchaseItem,
)

from .forms import (
    SupplierForm,
    InventoryItemForm,
    PurchaseForm,
    PurchaseItemFormSet,
)


# =========================================================
# SUPPLIER
# =========================================================

class SupplierListView(LoginRequiredMixin, ListView):

    model = Supplier
    template_name = "purchases/supplier_list.html"
    context_object_name = "suppliers"
    ordering = ["name"]


class SupplierCreateView(LoginRequiredMixin, CreateView):

    model = Supplier
    form_class = SupplierForm
    template_name = "purchases/supplier_form.html"
    success_url = reverse_lazy("supplier_list")

    def form_valid(self, form):

        form.instance.created_by = self.request.user

        messages.success(
            self.request,
            "Supplier added successfully."
        )

        return super().form_valid(form)


class SupplierUpdateView(LoginRequiredMixin, UpdateView):

    model = Supplier
    form_class = SupplierForm
    template_name = "purchases/supplier_form.html"
    success_url = reverse_lazy("supplier_list")

    def form_valid(self, form):

        messages.success(
            self.request,
            "Supplier updated successfully."
        )

        return super().form_valid(form)


class SupplierDeleteView(LoginRequiredMixin, DeleteView):

    model = Supplier
    template_name = "purchases/supplier_confirm_delete.html"
    success_url = reverse_lazy("supplier_list")

    def form_valid(self, form):

        messages.success(
            self.request,
            "Supplier deleted successfully."
        )

        return super().form_valid(form)


class SupplierDetailView(LoginRequiredMixin, DetailView):
    model = Supplier
    template_name = "purchases/supplier_detail.html"
    context_object_name = "supplier"

# =========================================================
# INVENTORY ITEM
# =========================================================

class InventoryItemListView(LoginRequiredMixin, ListView):

    model = InventoryItem
    template_name = "purchases/inventoryitem_list.html"
    context_object_name = "items"
    ordering = ["name"]


class InventoryItemCreateView(LoginRequiredMixin, CreateView):

    model = InventoryItem
    form_class = InventoryItemForm
    template_name = "purchases/inventoryitem_form.html"
    success_url = reverse_lazy("inventoryitem_list")

    def form_valid(self, form):

        messages.success(
            self.request,
            "Inventory item added successfully."
        )

        return super().form_valid(form)


class InventoryItemUpdateView(LoginRequiredMixin, UpdateView):

    model = InventoryItem
    form_class = InventoryItemForm
    template_name = "purchases/inventoryitem_form.html"
    success_url = reverse_lazy("inventoryitem_list")

    def form_valid(self, form):

        messages.success(
            self.request,
            "Inventory item updated successfully."
        )

        return super().form_valid(form)


class InventoryItemDeleteView(LoginRequiredMixin, DeleteView):

    model = InventoryItem
    template_name = "purchases/inventoryitem_confirm_delete.html"
    success_url = reverse_lazy("inventoryitem_list")

    def form_valid(self, form):

        messages.success(
            self.request,
            "Inventory item deleted successfully."
        )

        return super().form_valid(form)


# =========================================================
# PURCHASE LIST
# =========================================================

class PurchaseListView(LoginRequiredMixin, ListView):

    model = Purchase
    template_name = "purchases/purchase_list.html"
    context_object_name = "purchases"

    def get_queryset(self):

        return Purchase.objects.select_related(
            "supplier"
        ).prefetch_related(
            "items__item"
        ).order_by("-date", "-id")


# =========================================================
# PURCHASE CREATE
# =========================================================

class PurchaseCreateView(LoginRequiredMixin, CreateView):

    model = Purchase
    form_class = PurchaseForm
    template_name = "purchases/purchase_form.html"

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        if self.request.POST:

            context["formset"] = PurchaseItemFormSet(
                self.request.POST
            )

        else:

            context["formset"] = PurchaseItemFormSet()

        return context

    @transaction.atomic
    def form_valid(self, form):

        formset = PurchaseItemFormSet(
            self.request.POST
        )

        if not formset.is_valid():

            return self.render_to_response(
                self.get_context_data(
                    form=form
                )
            )

        purchase = form.save(
            commit=False
        )

        purchase.added_by = self.request.user

        purchase.total_amount = Decimal("0.00")

        purchase.save()

        formset.instance = purchase

        items = formset.save()

        total = Decimal("0.00")

        for item in items:

            total += (
                item.quantity *
                item.unit_price
            )

        purchase.total_amount = total

        purchase.save(
            update_fields=["total_amount"]
        )

        messages.success(
            self.request,
            "Purchase created successfully."
        )

        return redirect(
            "purchase_list"
        )


# =========================================================
# PURCHASE DETAIL
# =========================================================

class PurchaseDetailView(LoginRequiredMixin, DetailView):

    model = Purchase
    template_name = "purchases/purchase_detail.html"
    context_object_name = "purchase"

    def get_queryset(self):

        return Purchase.objects.select_related(
            "supplier"
        ).prefetch_related(
            "items__item"
        )


# =========================================================
# PURCHASE UPDATE
# =========================================================

class PurchaseUpdateView(LoginRequiredMixin, UpdateView):

    model = Purchase
    form_class = PurchaseForm
    template_name = "purchases/purchase_form.html"

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        if self.request.POST:

            context["formset"] = PurchaseItemFormSet(
                self.request.POST,
                instance=self.object
            )

        else:

            context["formset"] = PurchaseItemFormSet(
                instance=self.object
            )

        return context

    @transaction.atomic
    def form_valid(self, form):

        formset = PurchaseItemFormSet(
            self.request.POST,
            instance=self.object
        )

        if not formset.is_valid():

            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    formset=formset
                )
            )

        purchase = form.save()

        formset.instance = purchase

        formset.save()

        total = Decimal("0.00")

        for item in purchase.items.all():

            total += (
                item.quantity *
                item.unit_price
            )

        purchase.total_amount = total

        purchase.save(
            update_fields=["total_amount"]
        )

        messages.success(
            self.request,
            "Purchase updated successfully."
        )

        return redirect(
            "purchase_list"
        )


# =========================================================
# PURCHASE DELETE
# =========================================================

class PurchaseDeleteView(LoginRequiredMixin, DeleteView):

    model = Purchase
    template_name = "purchases/purchase_confirm_delete.html"
    success_url = reverse_lazy("purchase_list")

    def form_valid(self, form):

        messages.success(
            self.request,
            "Purchase deleted successfully."
        )

        return super().form_valid(form)