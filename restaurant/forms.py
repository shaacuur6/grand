from decimal import Decimal

from django import forms

from .models import FoodCategory, FoodItem, Employee


class BootstrapModelForm(forms.ModelForm):
    def apply_bootstrap(self):
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
                field.widget.attrs.setdefault("class", "form-select")
            else:
                field.widget.attrs.setdefault("class", "form-control")


class FoodCategoryForm(BootstrapModelForm):
    class Meta:
        model = FoodCategory
        fields = ["name"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs); self.apply_bootstrap()


class FoodForm(BootstrapModelForm):
    class Meta:
        model = FoodItem
        fields = ["name", "category", "price", "image"]
        widgets = {"price": forms.NumberInput(attrs={"step": "0.01", "min": "0"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs); self.apply_bootstrap()

    def clean_price(self):
        value = self.cleaned_data["price"]
        if value < Decimal("0.00"):
            raise forms.ValidationError("Price cannot be negative.")
        return value


class EmployeeForm(BootstrapModelForm):
    class Meta:
        model = Employee
        fields = ["employee_no", "full_name", "phone", "position", "active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs); self.apply_bootstrap()


class OrderContextForm(forms.Form):
    table_number = forms.IntegerField(required=False, min_value=1)
    booking = forms.IntegerField(required=False)
    employee = forms.IntegerField(required=False)
