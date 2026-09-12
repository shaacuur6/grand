from django import forms
from hotel.models import Room, Guest, Booking


class ReportFilterForm(forms.Form):
    start_date = forms.DateField(required=False, label="From", widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}))
    end_date = forms.DateField(required=False, label="To", widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}))
    check_out_from = forms.DateField(required=False, label="Checkout From", widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}))
    check_out_to = forms.DateField(required=False, label="Checkout To", widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}))
    room = forms.ModelChoiceField(queryset=Room.objects.all(), required=False, empty_label="All Rooms", widget=forms.Select(attrs={"class": "form-select"}))
    room_type = forms.ChoiceField(required=False, choices=[("", "All Room Types")] + list(Room.ROOM_TYPES), widget=forms.Select(attrs={"class": "form-select"}))
    guest = forms.ModelChoiceField(queryset=Guest.objects.all(), required=False, empty_label="All Guests", widget=forms.Select(attrs={"class": "form-select"}))
    status = forms.ChoiceField(required=False, choices=[("", "All Status")] + list(Booking.BOOKING_STATUS), widget=forms.Select(attrs={"class": "form-select"}))
    search = forms.CharField(required=False, label="Guest / Phone / Room", widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Name, phone or room..."}))

    def clean(self):
        data = super().clean()
        if data.get("start_date") and data.get("end_date") and data["start_date"] > data["end_date"]:
            raise forms.ValidationError("Check-in From date cannot be after To date.")
        if data.get("check_out_from") and data.get("check_out_to") and data["check_out_from"] > data["check_out_to"]:
            raise forms.ValidationError("Checkout From date cannot be after To date.")
        return data
