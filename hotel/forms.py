from datetime import date
from decimal import Decimal
from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from .models import Booking, Guest, Service, Room

BOOTSTRAP = "form-control"
SELECT = "form-select"


class BootstrapModelForm(forms.ModelForm):
    def _bootstrap(self):
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
                field.widget.attrs.setdefault("class", SELECT)
            else:
                field.widget.attrs.setdefault("class", BOOTSTRAP)


class GuestForm(BootstrapModelForm):
    class Meta:
        model = Guest
        fields = ["first_name", "last_name", "phone", "email", "address"]
        widgets = {"address": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._bootstrap()


class RoomForm(BootstrapModelForm):
    class Meta:
        model = Room
        fields = ["number", "room_type", "price", "price_with_ac", "status"]
        widgets = {
            "price": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "price_with_ac": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
        }

    def clean(self):
        return super().clean()

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.is_available = instance.status == "available"
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class BookingForm(BootstrapModelForm):
    class Meta:
        model = Booking
        fields = ["guest", "room", "check_in", "check_out", "with_ac"]
        widgets = {
            "check_in": forms.DateInput(attrs={"type": "date"}),
            "check_out": forms.DateInput(attrs={"type": "date"}),
            "with_ac": forms.CheckboxInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        qs = Room.objects.exclude(status__in=["maintenance", "out_of_order"])
        if self.instance and self.instance.pk:
            qs = Room.objects.filter(Q(pk=self.instance.room_id) | ~Q(status__in=["maintenance", "out_of_order"]))
        self.fields["room"].queryset = qs.order_by("number")
        self._bootstrap()

    def clean(self):
        cleaned = super().clean()
        room = cleaned.get("room")
        check_in = cleaned.get("check_in")
        check_out = cleaned.get("check_out")
        if check_in and check_out and check_out <= check_in:
            self.add_error("check_out", "Check-out must be after check-in.")
        if room and check_in and not self.instance.pk and not room.room_is_available(check_in):
            self.add_error("room", "This room is already booked for the selected date.")
        if room:
            cleaned["room_price"] = room.rate_for(cleaned.get("with_ac", False))
        return cleaned


class BookingUpdateForm(BootstrapModelForm):
    """Normal booking edit. Room is intentionally excluded; use Transfer Room."""
    class Meta:
        model = Booking
        fields = ["guest", "check_out", "with_ac"]
        widgets = {
            "check_out": forms.DateInput(attrs={"type": "date"}),
            "with_ac": forms.CheckboxInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._bootstrap()

    def clean(self):
        cleaned = super().clean()
        check_out = cleaned.get("check_out")
        if check_out and self.instance.check_in and check_out <= self.instance.check_in:
            self.add_error("check_out", "Check-out must be after check-in.")
        return cleaned


class RoomTransferForm(forms.Form):
    room = forms.ModelChoiceField(
        queryset=Room.objects.none(),
        widget=forms.Select(attrs={"class": SELECT}),
        label="New room",
    )
    transfer_date = forms.DateField(
        initial=date.today,
        widget=forms.DateInput(attrs={"type": "date", "class": BOOTSTRAP}),
    )
    note = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": BOOTSTRAP, "placeholder": "Reason / note"}),
    )

    def __init__(self, *args, booking=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.booking = booking
        self.fields["room"].queryset = Room.objects.filter(
            is_available=True, status="available"
        ).exclude(pk=getattr(booking, "room_id", None)).order_by("number")

    def clean(self):
        cleaned = super().clean()
        room = cleaned.get("room")
        transfer_date = cleaned.get("transfer_date")
        today = date.today()
        if not self.booking:
            return cleaned
        if transfer_date and transfer_date != today:
            raise ValidationError("A live room transfer must be recorded for today.")
        if transfer_date and transfer_date < self.booking.check_in:
            raise ValidationError("Transfer date cannot be before check-in.")
        if room and transfer_date and not room.room_is_available(transfer_date, exclude_booking=self.booking):
            raise ValidationError("The selected room is not available on the transfer date.")
        return cleaned


class CheckoutForm(forms.Form):
    discount = forms.DecimalField(
        required=False, initial=Decimal("0.00"), min_value=0,
        widget=forms.NumberInput(attrs={"class": BOOTSTRAP, "step": "0.01", "min": "0"}),
    )
    late_checkout_approved = forms.BooleanField(
        required=False,
        label="Approve late checkout",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    note = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": BOOTSTRAP, "rows": 2}),
    )


class ServiceForm(BootstrapModelForm):
    class Meta:
        model = Service
        fields = ["booking", "service_type", "description", "total_amount", "date"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "total_amount": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["booking"].queryset = Booking.objects.filter(
            status="checked_in"
        ).select_related("guest", "room").order_by("-check_in", "id")
        self._bootstrap()
