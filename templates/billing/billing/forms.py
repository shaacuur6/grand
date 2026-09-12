from django import forms
from decimal import Decimal


class PaymentForm(forms.Form):
    amount = forms.DecimalField(min_value=Decimal("0.01"), widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0.01"}))
    payment_method = forms.ChoiceField(choices=[("cash", "Cash"), ("card", "Card"), ("bank", "Bank Transfer"), ("mobile", "Mobile Money")], widget=forms.Select(attrs={"class": "form-select"}))

class InvoiceFilterForm(forms.Form):

    check_in_from = forms.DateField(
        required=False,
        label="Check-in From",
        widget=forms.DateInput(attrs={
            "type": "date",
            "class": "form-control"
        })
    )

    check_in_to = forms.DateField(
        required=False,
        label="Check-in To",
        widget=forms.DateInput(attrs={
            "type": "date",
            "class": "form-control"
        })
    )

    check_out_from = forms.DateField(
        required=False,
        label="Check-out From",
        widget=forms.DateInput(attrs={
            "type": "date",
            "class": "form-control"
        })
    )

    check_out_to = forms.DateField(
        required=False,
        label="Check-out To",
        widget=forms.DateInput(attrs={
            "type": "date",
            "class": "form-control"
        })
    )

    guest_name = forms.CharField(
        required=False,
        label="Guest",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Search guest..."
        })
    )

    status = forms.ChoiceField(
        required=False,
        choices=[
            ("", "All"),
            ("checked_in", "Active"),
            ("checked_out", "Completed"),
        ],
        widget=forms.Select(attrs={
            "class": "form-control"
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs.update({
                "class": "form-control"
            })

        self.fields["guest_name"].widget.attrs.update({
            "placeholder": "Search guest..."
        })