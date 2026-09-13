from decimal import Decimal

from django import forms


class BootstrapFormMixin:
    def apply_bootstrap(self):
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
                field.widget.attrs.setdefault("class", "form-select")
            else:
                field.widget.attrs.setdefault("class", "form-control")


class PaymentForm(BootstrapFormMixin, forms.Form):
    amount = forms.DecimalField(
        min_value=Decimal("0.01"),
        max_digits=10, decimal_places=2,
        widget=forms.NumberInput(attrs={"step": "0.01", "min": "0.01"}),
    )
    payment_method = forms.ChoiceField(
        choices=[
            ("cash", "Cash"), ("card", "Card"),
            ("bank", "Bank Transfer"), ("mobile", "Mobile Money"),
        ]
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()


class InvoiceFilterForm(BootstrapFormMixin, forms.Form):
    check_in_from = forms.DateField(required=False, label="Check-in From", widget=forms.DateInput(attrs={"type": "date"}))
    check_in_to = forms.DateField(required=False, label="Check-in To", widget=forms.DateInput(attrs={"type": "date"}))
    check_out_from = forms.DateField(required=False, label="Check-out From", widget=forms.DateInput(attrs={"type": "date"}))
    check_out_to = forms.DateField(required=False, label="Check-out To", widget=forms.DateInput(attrs={"type": "date"}))
    guest_name = forms.CharField(required=False, label="Guest / phone")
    status = forms.ChoiceField(required=False, choices=[("", "All"), ("reserved", "Reserved"), ("checked_in", "Active"), ("checked_out", "Completed")])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()

    def clean(self):
        data = super().clean()
        if data.get("check_in_from") and data.get("check_in_to") and data["check_in_from"] > data["check_in_to"]:
            raise forms.ValidationError("Check-in From cannot be after Check-in To.")
        if data.get("check_out_from") and data.get("check_out_to") and data["check_out_from"] > data["check_out_to"]:
            raise forms.ValidationError("Check-out From cannot be after Check-out To.")
        return data
