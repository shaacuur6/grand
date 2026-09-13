from decimal import Decimal

from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory

from .models import Supplier, InventoryItem, Purchase, PurchaseItem


class BootstrapModelForm(forms.ModelForm):
    def apply_bootstrap(self):
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
                field.widget.attrs.setdefault("class", "form-select")
            else:
                field.widget.attrs.setdefault("class", "form-control")


class SupplierForm(BootstrapModelForm):
    class Meta:
        model = Supplier
        fields = ["name", "contact_person", "phone", "email", "address"]
        widgets = {"address": forms.Textarea(attrs={"rows": 3})}
    def __init__(self, *args, **kwargs): super().__init__(*args, **kwargs); self.apply_bootstrap()


class InventoryItemForm(BootstrapModelForm):
    class Meta:
        model = InventoryItem
        fields = ["name", "unit", "current_stock", "reorder_level"]
        widgets = {"current_stock": forms.NumberInput(attrs={"step": "0.01", "min": "0"}), "reorder_level": forms.NumberInput(attrs={"step": "0.01", "min": "0"})}
    def __init__(self, *args, **kwargs): super().__init__(*args, **kwargs); self.apply_bootstrap()


class PurchaseForm(BootstrapModelForm):
    class Meta:
        model = Purchase
        fields = ["supplier", "date"]
    def __init__(self, *args, **kwargs): super().__init__(*args, **kwargs); self.apply_bootstrap()


class PurchaseItemForm(BootstrapModelForm):
    class Meta:
        model = PurchaseItem
        fields = ["item", "quantity", "unit_price", "description"]
        widgets = {"quantity": forms.NumberInput(attrs={"step": "0.01", "min": "0.01"}), "unit_price": forms.NumberInput(attrs={"step": "0.01", "min": "0"}), "description": forms.TextInput()}
    def __init__(self, *args, **kwargs): super().__init__(*args, **kwargs); self.apply_bootstrap()
    def clean_quantity(self):
        value = self.cleaned_data["quantity"]
        if value <= 0: raise forms.ValidationError("Quantity must be greater than zero.")
        return value
    def clean_unit_price(self):
        value = self.cleaned_data["unit_price"]
        if value < 0: raise forms.ValidationError("Unit price cannot be negative.")
        return value


PurchaseItemFormSet = inlineformset_factory(Purchase, PurchaseItem, form=PurchaseItemForm, extra=1, can_delete=True)
