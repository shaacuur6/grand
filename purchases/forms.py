from django import forms
from django.forms import inlineformset_factory

from .models import Supplier, InventoryItem, Purchase, PurchaseItem


class SupplierForm(forms.ModelForm):

    class Meta:
        model = Supplier
        fields = [
            "name",
            "contact_person",
            "phone",
            "email",
            "address",
        ]

        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "contact_person": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "phone": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control"}
            ),
            "address": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                }
            ),
        }


class InventoryItemForm(forms.ModelForm):

    class Meta:
        model = InventoryItem
        fields = [
            "name",
            "unit",
            "current_stock",
            "reorder_level",
        ]

        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "unit": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "current_stock": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                }
            ),
            "reorder_level": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                }
            ),
        }


class PurchaseForm(forms.ModelForm):

    class Meta:
        model = Purchase
        fields = [
            "supplier",
            "date",
        ]

        widgets = {
            "supplier": forms.Select(
                attrs={"class": "form-select"}
            ),
            "date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control",
                }
            ),
        }


class PurchaseItemForm(forms.ModelForm):

    class Meta:
        model = PurchaseItem

        fields = [
            "item",
            "quantity",
            "unit_price",
            "description",
        ]

        widgets = {
            "item": forms.Select(
                attrs={"class": "form-select"}
            ),
            "quantity": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "unit_price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "description": forms.TextInput(
                attrs={"class": "form-control"}
            ),
        }


PurchaseItemFormSet = inlineformset_factory(
    Purchase,
    PurchaseItem,
    form=PurchaseItemForm,
    extra=1,
    can_delete=True,
)