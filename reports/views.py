from decimal import Decimal
from datetime import datetime
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.views.generic import TemplateView

from accounts.mixins import RoleRequiredMixin
from hotel.models import Booking, Room, RoomStay
from .forms import ReportFilterForm


class HotelReportBase(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    allowed_roles = ["admin", "manager", "reception"]

    def filtered_bookings(self):
        form = ReportFilterForm(self.request.GET or None)
        qs = Booking.objects.select_related("guest", "room").prefetch_related("room_stays")
        if form.is_valid():
            d = form.cleaned_data
            if d.get("start_date"):
                qs = qs.filter(check_in__gte=d["start_date"])
            if d.get("end_date"):
                qs = qs.filter(check_in__lte=d["end_date"])
            if d.get("check_out_from"):
                qs = qs.filter(check_out__gte=d["check_out_from"])
            if d.get("check_out_to"):
                qs = qs.filter(check_out__lte=d["check_out_to"])
            if d.get("room"):
                qs = qs.filter(room=d["room"])
            if d.get("room_type"):
                qs = qs.filter(room__room_type=d["room_type"])
            if d.get("guest"):
                qs = qs.filter(guest=d["guest"])
            if d.get("status"):
                qs = qs.filter(status=d["status"])
            if d.get("search"):
                term = d["search"]
                search_q = (
                    Q(guest__first_name__icontains=term)
                    | Q(guest__last_name__icontains=term)
                    | Q(guest__phone__icontains=term)
                )
                if term.isdigit():
                    search_q |= Q(room__number=int(term))
                qs = qs.filter(search_q)
        return form, qs.distinct()


class DailyCheckInsReportView(HotelReportBase):
    template_name = "reports/hotel/daily_checkins.html"

    def get_context_data(self, **kwargs):
        c = super().get_context_data(**kwargs)
        form, qs = self.filtered_bookings()
        c.update({"form": form, "bookings": qs.order_by("-check_in", "room__number")})
        return c


class DailyCheckOutsReportView(HotelReportBase):
    template_name = "reports/hotel/daily_checkouts.html"

    def get_context_data(self, **kwargs):
        c = super().get_context_data(**kwargs)
        form, qs = self.filtered_bookings()
        if not self.request.GET:
            qs = qs.filter(check_out=timezone.now().date())
        else:
            qs = qs.filter(check_out__isnull=False)
        c.update({"form": form, "bookings": qs.order_by("-check_out", "room__number")})
        return c


class ReservationReportView(HotelReportBase):
    template_name = "reports/hotel/reservation_report.html"

    def get_context_data(self, **kwargs):
        c = super().get_context_data(**kwargs)
        form, qs = self.filtered_bookings()
        c.update({
            "form": form,
            "bookings": qs.order_by("-created", "room__number"),
            "total_bookings": qs.count(),
        })
        return c


class GuestHistoryReportView(HotelReportBase):
    template_name = "reports/hotel/guest_history.html"

    def get_context_data(self, **kwargs):
        c = super().get_context_data(**kwargs)
        form, qs = self.filtered_bookings()
        c.update({"form": form, "bookings": qs.order_by("-check_in"), "total_bookings": qs.count()})
        return c


class RoomRevenueReportView(HotelReportBase):
    template_name = "reports/hotel/room_revenue.html"

    def get_context_data(self, **kwargs):
        c = super().get_context_data(**kwargs)
        form, qs = self.filtered_bookings()
        stay_qs = RoomStay.objects.filter(booking__in=qs).select_related("booking__guest", "room")
        report = []
        total = Decimal("0.00")
        for stay in stay_qs:
            # For active stays, value through today.
            end = stay.end_date or timezone.now().date()
            nights = max((end - stay.start_date).days, 0)
            amount = Decimal(nights) * stay.rate
            report.append({"stay": stay, "nights": nights, "amount": amount})
            total += amount
        c.update({"form": form, "report": report, "total_revenue": total})
        return c


class StayLedgerReportView(HotelReportBase):
    template_name = "reports/hotel/stay_ledger.html"

    def get_context_data(self, **kwargs):
        c = super().get_context_data(**kwargs)
        form, bookings = self.filtered_bookings()
        stays = RoomStay.objects.filter(booking__in=bookings).select_related(
            "booking__guest", "room"
        ).order_by("-start_date", "room__number")
        rows = []
        total = Decimal("0.00")
        for stay in stays:
            end = stay.end_date or timezone.now().date()
            nights = max((end - stay.start_date).days, 0)
            amount = Decimal(nights) * stay.rate
            rows.append({"stay": stay, "nights": nights, "amount": amount})
            total += amount
        c.update({"form": form, "rows": rows, "total": total})
        return c


class OccupancyReportView(HotelReportBase):
    template_name = "reports/hotel/occupancy_report.html"

    def get_context_data(self, **kwargs):
        c = super().get_context_data(**kwargs)
        day = self.request.GET.get("start_date") or str(timezone.now().date())
        try:
            selected = datetime.strptime(day, "%Y-%m-%d").date()
        except ValueError:
            selected = timezone.now().date()
        occupied = RoomStay.objects.filter(
            start_date__lte=selected
        ).filter(Q(end_date__isnull=True) | Q(end_date__gt=selected)).values("room").distinct().count()
        total = Room.objects.count()
        c.update({
            "selected_date": selected,
            "total_rooms": total,
            "occupied_rooms": occupied,
            "vacant_rooms": max(total - occupied, 0),
            "occupancy_rate": (occupied / total * 100) if total else 0,
            "form": ReportFilterForm(self.request.GET or None),
        })
        return c


class AvailableRoomsReportView(HotelReportBase):
    template_name = "reports/hotel/available_rooms.html"

    def get_context_data(self, **kwargs):
        c = super().get_context_data(**kwargs)
        c["rooms"] = Room.objects.filter(status="available").order_by("number")
        return c


class OccupiedRoomsReportView(HotelReportBase):
    template_name = "reports/hotel/occupied_rooms.html"

    def get_context_data(self, **kwargs):
        c = super().get_context_data(**kwargs)
        c["rooms"] = Room.objects.filter(status="occupied").order_by("number")
        return c


class RoomCleaningReportView(HotelReportBase):
    template_name = "reports/hotel/room_cleaning.html"

    def get_context_data(self, **kwargs):
        c = super().get_context_data(**kwargs)
        c["rooms"] = Room.objects.filter(status="cleaning").order_by("number")
        return c


class MaintenanceReportView(HotelReportBase):
    template_name = "reports/hotel/maintenance_report.html"

    def get_context_data(self, **kwargs):
        c = super().get_context_data(**kwargs)
        c["rooms"] = Room.objects.filter(status__in=["maintenance", "out_of_order"]).order_by("number")
        return c


class RoomTypeRevenueReportView(HotelReportBase):
    template_name = "reports/hotel/room_type_revenue.html"

    def get_context_data(self, **kwargs):
        c = super().get_context_data(**kwargs)
        form, bookings = self.filtered_bookings()
        stays = RoomStay.objects.filter(booking__in=bookings).select_related("room")
        totals = {}
        for stay in stays:
            end = stay.end_date or timezone.now().date()
            nights = max((end - stay.start_date).days, 0)
            totals.setdefault(stay.room.room_type, Decimal("0.00"))
            totals[stay.room.room_type] += Decimal(nights) * stay.rate
        c.update({"form": form, "report": [{"room_type": k, "total": v} for k, v in totals.items()]})
        return c
