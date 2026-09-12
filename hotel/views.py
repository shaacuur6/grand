from datetime import time
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView, FormView

from accounts.mixins import RoleRequiredMixin
from billing.models import Invoice
from billing.services import get_financial_summary, sync_invoice
from restaurant.models import Order
from .forms import (
    BookingForm, BookingUpdateForm, CheckoutForm, GuestForm, RoomForm,
    RoomTransferForm, ServiceForm,
)
from .models import Room, Booking, Guest, Service, RoomStay
from .utils import ensure_room_stay
from accounts.constants import ALL_ROLES, MANAGEMENT_ROLES, ADMIN_ROLES

#ROLES = ["admin", "manager", "reception"]
CHECKOUT_CUTOFF = time(13, 0)


def hotel_now():
    return timezone.localtime() if timezone.is_aware(timezone.now()) else timezone.now()


def is_late_checkout(dt):
    return dt.time() > CHECKOUT_CUTOFF

    
class BookingListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    allowed_roles = ALL_ROLES
    model = Booking
    template_name = "hotel/booking_list.html"
    context_object_name = "bookings"

    def get_queryset(self):
        return Booking.objects.filter(
            status__in=["reserved", "checked_in"]
        ).select_related("guest", "room").prefetch_related("room_stays").order_by("-check_in", "-id")


class BookingDetailView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    allowed_roles = ALL_ROLES
    template_name = "hotel/booking_detail.html"

    def dispatch(self, request, *args, **kwargs):
        self.booking = get_object_or_404(
            Booking.objects.select_related("guest", "room"), pk=kwargs["pk"]
        )
        ensure_room_stay(self.booking)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        booking = self.booking
        invoice = Invoice.objects.filter(booking=booking).first()
        if booking.status in {"reserved", "checked_in", "checked_out"}:
            if not invoice and booking.status in {"checked_in", "checked_out"}:
                invoice = sync_invoice(booking, as_of=booking.check_out or timezone.localdate())
        summary = get_financial_summary(
            booking,
            as_of=booking.check_out or timezone.localdate(),
            include_checkout_night=booking.status == "checked_out",
        )
        orders = Order.objects.filter(booking=booking).prefetch_related("items__food").order_by("created_at", "id")
        services = booking.services.all().order_by("date", "id")
        context.update({
            "booking": booking,
            "invoice": invoice,
            "summary": summary,
            "room_stays": booking.stays,
            "orders": orders,
            "services": services,
        })
        return context


class BookingCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    allowed_roles = ALL_ROLES
    model = Booking
    form_class = BookingForm
    template_name = "hotel/booking_form.html"
    success_url = reverse_lazy("booking_list")

    @transaction.atomic
    def form_valid(self, form):
        booking = form.save(commit=False)
        booking.created_by = self.request.user
        booking.status = "reserved"
        booking.room_price = booking.room.rate_for(booking.with_ac)
        booking.save()
        room = Room.objects.select_for_update().get(pk=booking.room_id)
        room.is_available = False
        room.status = "reserved"
        room.save(update_fields=["is_available", "status"])
        ensure_room_stay(booking)
        messages.success(self.request, f"Booking #{booking.pk} created successfully.")
        return redirect("booking_detail", pk=booking.pk)


class BookingUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    allowed_roles = MANAGEMENT_ROLES
    model = Booking
    form_class = BookingUpdateForm
    template_name = "hotel/booking_form.html"

    @transaction.atomic
    def form_valid(self, form):
        booking = self.get_object()
        old_ac = booking.with_ac
        new_ac = form.cleaned_data["with_ac"]
        booking = form.save(commit=False)
        booking.updated_by = self.request.user
        booking.room_price = booking.room.rate_for(new_ac)
        booking.save()

        if old_ac != new_ac and booking.status == "checked_in":
            today = hotel_now().date()
            current = booking.room_stays.select_for_update().filter(end_date__isnull=True).last()
            new_rate = booking.room.rate_for(new_ac)
            if current and current.start_date == today:
                current.rate = new_rate
                current.with_ac = new_ac
                current.note = "AC/rate changed"
                current.save(update_fields=["rate", "with_ac", "note"])
            elif current:
                current.end_date = today
                current.save(update_fields=["end_date"])
                RoomStay.objects.create(
                    booking=booking, room=booking.room, start_date=today,
                    rate=new_rate, with_ac=new_ac, note="AC/rate changed"
                )
            sync_invoice(booking)

        messages.success(self.request, f"Booking #{booking.pk} updated successfully.")
        return redirect("booking_detail", pk=booking.pk)


class CheckInView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ALL_ROLES

    @transaction.atomic
    def post(self, request, pk):
        booking = get_object_or_404(Booking.objects.select_for_update().select_related("room"), pk=pk)
        if booking.status != "reserved":
            messages.error(request, "Only reserved bookings can be checked in.")
            return redirect("booking_detail", pk=pk)
        if booking.check_in > hotel_now().date():
            messages.error(request, "This booking is for a future date and cannot be checked in yet.")
            return redirect("booking_detail", pk=pk)
        if not booking.room.room_is_available(hotel_now().date(), exclude_booking=booking):
            messages.error(request, "The room is not available.")
            return redirect("booking_detail", pk=pk)
        booking.status = "checked_in"
        booking.actual_check_in_at = hotel_now()
        booking.updated_by = request.user
        booking.save(update_fields=["status", "actual_check_in_at", "updated_by", "updated"])
        room = Room.objects.select_for_update().get(pk=booking.room_id)
        room.is_available = False
        room.status = "occupied"
        room.save(update_fields=["is_available", "status"])
        ensure_room_stay(booking)
        sync_invoice(booking)
        messages.success(request, f"Booking #{booking.pk} checked in.")
        return redirect("booking_detail", pk=pk)

    def get(self, request, pk):
        return self.post(request, pk)


class RoomTransferView(LoginRequiredMixin, RoleRequiredMixin, FormView):
    allowed_roles = MANAGEMENT_ROLES
    template_name = "hotel/room_transfer_form.html"
    form_class = RoomTransferForm

    def dispatch(self, request, *args, **kwargs):
        self.booking = get_object_or_404(
            Booking.objects.select_related("guest", "room"), pk=kwargs["pk"]
        )
        if self.booking.status != "checked_in":
            messages.error(request, "Only checked-in bookings can be transferred.")
            return redirect("booking_detail", pk=self.booking.pk)
        ensure_room_stay(self.booking)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["booking"] = self.booking
        return kwargs
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["booking"] = self.booking
        return context

    @transaction.atomic
    def form_valid(self, form):
        booking = Booking.objects.select_for_update().select_related("room").get(pk=self.booking.pk)
        old_room = Room.objects.select_for_update().get(pk=booking.room_id)
        new_room = Room.objects.select_for_update().get(pk=form.cleaned_data["room"].pk)
        transfer_date = form.cleaned_data["transfer_date"]
        note = form.cleaned_data.get("note", "")

        if not new_room.room_is_available(transfer_date, exclude_booking=booking):
            form.add_error("room", "The selected room is no longer available.")
            return self.form_invalid(form)

        current = booking.room_stays.select_for_update().filter(end_date__isnull=True).last()
        new_rate = new_room.rate_for(booking.with_ac)

        # Same-day transfer: replace the current room segment. No night is lost or duplicated.
        if current and current.start_date == transfer_date:
            current.room = new_room
            current.rate = new_rate
            current.with_ac = booking.with_ac
            current.note = note or f"Same-day transfer from room {old_room.number}"
            current.save(update_fields=["room", "rate", "with_ac", "note"])
        else:
            if current:
                current.end_date = transfer_date
                current.save(update_fields=["end_date"])
            RoomStay.objects.create(
                booking=booking,
                room=new_room,
                start_date=transfer_date,
                rate=new_rate,
                with_ac=booking.with_ac,
                note=note or f"Transferred from room {old_room.number}",
            )

        old_room.is_available = True
        old_room.status = "available"
        old_room.save(update_fields=["is_available", "status"])
        new_room.is_available = False
        new_room.status = "occupied"
        new_room.save(update_fields=["is_available", "status"])

        booking.room = new_room
        booking.room_price = new_rate
        booking.updated_by = self.request.user
        booking.save(update_fields=["room", "room_price", "updated_by", "updated"])

        # Recalculate the invoice from the room ledger. Payments remain untouched.
        sync_invoice(booking)
        messages.success(
            self.request,
            f"Room transferred from {old_room.number} to {new_room.number}. "
            f"Existing payments were preserved; new charges use the new room rate."
        )
        return redirect("booking_detail", pk=booking.pk)


class BookingCheckOutView(LoginRequiredMixin, RoleRequiredMixin, FormView):
    allowed_roles = ALL_ROLES
    template_name = "hotel/booking_checkout.html"
    form_class = CheckoutForm

    def dispatch(self, request, *args, **kwargs):
        self.booking = get_object_or_404(
            Booking.objects.select_related("guest", "room"), pk=kwargs["pk"]
        )
        if self.booking.status != "checked_in":
            messages.error(request, "Only checked-in bookings can be checked out.")
            return redirect("booking_detail", pk=self.booking.pk)
        ensure_room_stay(self.booking)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = hotel_now()
        summary = get_financial_summary(
            self.booking,
            as_of=now.date(),
            include_checkout_night=True,
        )
        context.update({"booking": self.booking, "summary": summary, "late": is_late_checkout(now)})
        return context

    @transaction.atomic
    def form_valid(self, form):
        booking = Booking.objects.select_for_update().select_related("room").get(pk=self.booking.pk)
        now = hotel_now()
        checkout_date = now.date()
        late = is_late_checkout(now)

        summary = get_financial_summary(booking, as_of=checkout_date, include_checkout_night=True)
        discount = form.cleaned_data.get("discount") or Decimal("0.00")
        if discount > summary["room_total"] + summary["restaurant_total"] + summary["service_total"]:
            form.add_error("discount", "Discount cannot exceed the subtotal.")
            return self.form_invalid(form)

        invoice = Invoice.objects.filter(booking=booking).first() or sync_invoice(booking)
        invoice.discount = discount
        invoice.room_total = summary["room_total"]
        invoice.restaurant_total = summary["restaurant_total"]
        invoice.service_total = summary["service_total"]
        invoice.total = max(
            Decimal("0.00"),
            invoice.room_total + invoice.restaurant_total + invoice.service_total - discount
        )
        invoice.save(update_fields=["room_total", "restaurant_total", "service_total", "discount", "total"])

        current = booking.room_stays.select_for_update().filter(end_date__isnull=True).last()
        if current:
            current.end_date = checkout_date
            current.save(update_fields=["end_date"])

        booking.status = "checked_out"
        booking.actual_check_out_at = now
        booking.late_checkout_approved = form.cleaned_data.get("late_checkout_approved", False)
        booking.late_checkout_charge = current.rate if (late and booking.late_checkout_approved and current) else Decimal("0.00")
        booking.check_out = checkout_date
        booking.updated_by = self.request.user
        booking.save(update_fields=[
            "status", "actual_check_out_at", "late_checkout_approved",
            "late_checkout_charge", "check_out", "updated_by", "updated"
        ])

        room = Room.objects.select_for_update().get(pk=booking.room_id)
        room.is_available = True
        room.status = "available"
        room.save(update_fields=["is_available", "status"])

        # Add the late checkout charge to the final invoice only when approved.
        if late and booking.late_checkout_approved and current:
            invoice.room_total += current.rate
            invoice.total = max(
                Decimal("0.00"),
                invoice.room_total + invoice.restaurant_total + invoice.service_total - invoice.discount
            )
            invoice.save(update_fields=["room_total", "total"])

        messages.success(request, f"Booking #{booking.pk} checked out. Final balance: ${invoice.total - sum((p.amount for p in invoice.payment_set.all()), Decimal('0.00')):,.2f}")
        return redirect("booking_detail", pk=booking.pk)


class CheckOutView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ALL_ROLES
    def get(self, request, pk):
        return redirect("booking_check_out", pk=pk)


class RoomListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    allowed_roles = ALL_ROLES
    model = Room
    template_name = "hotel/room_list.html"
    context_object_name = "rooms"
    queryset = Room.objects.all().order_by("number")


class RoomCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    allowed_roles = MANAGEMENT_ROLES
    model = Room
    form_class = RoomForm
    template_name = "hotel/room_form.html"
    success_url = reverse_lazy("room_list")
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class RoomUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    allowed_roles = MANAGEMENT_ROLES
    model = Room
    form_class = RoomForm
    template_name = "hotel/room_form.html"
    success_url = reverse_lazy("room_list")


class GuestListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    allowed_roles = ALL_ROLES
    model = Guest
    template_name = "hotel/guest_list.html"
    context_object_name = "guests"
    queryset = Guest.objects.all().order_by("first_name", "last_name")


class GuestCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    allowed_roles = ALL_ROLES
    model = Guest
    form_class = GuestForm
    template_name = "hotel/guest_form.html"
    success_url = reverse_lazy("guest_list")
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class GuestCreateAjaxView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    allowed_roles = ALL_ROLES
    model = Guest
    fields = ["first_name", "last_name", "phone", "email", "address"]
    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.created_by = self.request.user
        self.object.save()
        return JsonResponse({"id": self.object.id, "name": str(self.object)})
    def form_invalid(self, form):
        return JsonResponse({"errors": form.errors}, status=400)


class GuestUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    allowed_roles = ALL_ROLES
    model = Guest
    form_class = GuestForm
    template_name = "hotel/guest_form.html"
    success_url = reverse_lazy("guest_list")


class BookingDeleteView(LoginRequiredMixin, RoleRequiredMixin, DeleteView):
    allowed_roles = MANAGEMENT_ROLES
    model = Booking
    template_name = "hotel/booking_confirm_delete.html"
    success_url = reverse_lazy("booking_list")


class DashboardView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    allowed_roles = MANAGEMENT_ROLES
    template_name = "dashboard.html"


class ServiceListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    allowed_roles = ALL_ROLES
    model = Service
    template_name = "services/service_list.html"
    context_object_name = "services"
    queryset = Service.objects.select_related("booking", "booking__guest", "booking__room").order_by("-date", "-id")


class ServiceCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    allowed_roles = ALL_ROLES
    model = Service
    form_class = ServiceForm
    template_name = "services/service_form.html"
    success_url = reverse_lazy("service_list")
    @transaction.atomic
    def form_valid(self, form):
        form.instance.added_by = self.request.user
        response = super().form_valid(form)
        sync_invoice(self.object.booking)
        return response


class ServiceUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    allowed_roles = MANAGEMENT_ROLES
    model = Service
    form_class = ServiceForm
    template_name = "services/service_form.html"
    success_url = reverse_lazy("service_list")
    @transaction.atomic
    def form_valid(self, form):
        old_booking = self.get_object().booking
        response = super().form_valid(form)
        sync_invoice(old_booking)
        return response


class ServiceDeleteView(LoginRequiredMixin, RoleRequiredMixin, DeleteView):
    allowed_roles = MANAGEMENT_ROLES
    model = Service
    template_name = "services/service_confirm_delete.html"
    success_url = reverse_lazy("service_list")
    @transaction.atomic
    def form_valid(self, form):
        booking = self.get_object().booking
        response = super().form_valid(form)
        sync_invoice(booking)
        return response
