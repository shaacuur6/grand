from django import forms
from django.contrib.auth.models import User

from hotel.models import Booking, Room, Guest
from restaurant.models import FoodCategory, FoodItem
from purchases.models import Supplier


class ReportFilterForm(forms.Form):
    start_date = forms.DateField(required=False, label="From", widget=forms.DateInput(attrs={"type": "date"}))
    end_date = forms.DateField(required=False, label="To", widget=forms.DateInput(attrs={"type": "date"}))
    room = forms.ModelChoiceField(queryset=Room.objects.all().order_by("number"), required=False, empty_label="All rooms")
    room_type = forms.ChoiceField(required=False, choices=[("", "All room types")] + list(Room.ROOM_TYPES))
    guest = forms.ModelChoiceField(queryset=Guest.objects.all().order_by("first_name", "last_name"), required=False, empty_label="All guests")
    status = forms.ChoiceField(required=False, choices=[("", "All statuses")] + list(Booking.BOOKING_STATUS))
    search = forms.CharField(required=False, label="Search", widget=forms.TextInput(attrs={"placeholder": "Guest, phone or room"}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-select" if isinstance(field.widget, forms.Select) else "form-control")

    def clean(self):
        data = super().clean()
        if data.get("start_date") and data.get("end_date") and data["start_date"] > data["end_date"]:
            raise forms.ValidationError("From date cannot be after To date.")
        return data


class DateRangeForm(forms.Form):
    start_date = forms.DateField(required=False, label="From", widget=forms.DateInput(attrs={"type": "date"}))
    end_date = forms.DateField(required=False, label="To", widget=forms.DateInput(attrs={"type": "date"}))
    waiter = forms.ModelChoiceField(queryset=User.objects.filter(userprofile__role="waiter").order_by("username"), required=False, empty_label="All waiters")
    category = forms.ModelChoiceField(queryset=FoodCategory.objects.all().order_by("name"), required=False, empty_label="All categories")
    food = forms.ModelChoiceField(queryset=FoodItem.objects.all().order_by("name"), required=False, empty_label="All food")
    supplier = forms.ModelChoiceField(queryset=Supplier.objects.all().order_by("name"), required=False, empty_label="All suppliers")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-select" if isinstance(field.widget, forms.Select) else "form-control")

    def clean(self):
        data = super().clean()
        if data.get("start_date") and data.get("end_date") and data["start_date"] > data["end_date"]:
            raise forms.ValidationError("From date cannot be after To date.")
        return data
