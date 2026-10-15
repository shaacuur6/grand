from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, F, Q, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import render
from django.http import HttpResponse
from datetime import timedelta
from django.utils import timezone
from django.views.generic import TemplateView, View

from accounts.constants import MANAGEMENT_ROLES, REPORT_ROLES
from accounts.mixins import RoleRequiredMixin
from billing.models import (Invoice, Payment, RestaurantPaymentAllocation, RoomPaymentAllocation, ServicePaymentAllocation)
from hotel.models import Booking, Room, RoomStay, Guest, Service
from restaurant.models import FoodCategory, FoodItem, Order, OrderItem
from purchases.models import InventoryItem, Purchase, PurchaseItem, Supplier
from openpyxl import Workbook
from reportlab.pdfgen import canvas
from .forms import DateRangeForm, ReportFilterForm


class ReportBase(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    allowed_roles = REPORT_ROLES

    def date_range(self):
        form = DateRangeForm(self.request.GET or None)
        if not form.is_valid(): return form, None, None
        return form, form.cleaned_data.get("start_date"), form.cleaned_data.get("end_date")


class ReportsDashboardView(ReportBase):
    template_name = "reports/dashboard.html"
    def get_context_data(self, **kwargs):
        c = super().get_context_data(**kwargs)
        today = timezone.localdate()
        payments = Payment.objects.filter(created__date=today).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        sales = Order.objects.filter(created_at__date=today).aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
        c.update({
            "today": today, "room_count": Room.objects.count(),
            "occupied_count": Room.objects.filter(status="occupied").count(),
            "checkins": Booking.objects.filter(check_in=today).count(),
            "checkouts": Booking.objects.filter(check_out=today).count(),
            "collections": payments, "restaurant_sales": sales,
            "outstanding": sum((i.balance for i in Invoice.objects.all()), Decimal("0.00")),
            "low_stock": InventoryItem.objects.filter(current_stock__lte=F("reorder_level")).count(),
        })
        return c


class HotelReportBase(ReportBase):
    def filtered_bookings(self, apply_date_filters=True):
        form = ReportFilterForm(self.request.GET or None)
        qs = Booking.objects.select_related("guest", "room").prefetch_related("room_stays")
        if form.is_valid():
            d = form.cleaned_data
            if apply_date_filters and d.get("start_date"): qs = qs.filter(check_in__gte=d["start_date"])
            if apply_date_filters and d.get("end_date"): qs = qs.filter(check_in__lte=d["end_date"])
            if d.get("room"): qs = qs.filter(room=d["room"])
            if d.get("room_type"): qs = qs.filter(room__room_type=d["room_type"])
            if d.get("guest"): qs = qs.filter(guest=d["guest"])
            if d.get("status"): qs = qs.filter(status=d["status"])
            if d.get("search"):
                term=d["search"]; search_q=Q(guest__first_name__icontains=term)|Q(guest__last_name__icontains=term)|Q(guest__phone__icontains=term)
                if term.isdigit(): search_q |= Q(room__number=int(term))
                qs=qs.filter(search_q)
        return form, qs.distinct()


def filter_booking_dates(qs, form, field_name, today=None):
    """Apply an inclusive report range to check_in or check_out."""
    today = today or timezone.localdate()
    if not form.is_valid():
        return qs.none()
    start = form.cleaned_data.get("start_date")
    end = form.cleaned_data.get("end_date")
    if start:
        qs = qs.filter(**{f"{field_name}__gte": start})
    if end:
        qs = qs.filter(**{f"{field_name}__lte": end})
    if not start and not end:
        qs = qs.filter(**{field_name: today})
    return qs


class DailyCheckInsReportView(HotelReportBase):
    template_name="reports/hotel/daily_checkins.html"
    def get_context_data(self, **kwargs):
        c=super().get_context_data(**kwargs); form,qs=self.filtered_bookings(apply_date_filters=False); qs=filter_booking_dates(qs,form,"check_in"); c.update(form=form,bookings=qs.order_by("room__number")); return c


class DailyCheckOutsReportView(HotelReportBase):
    template_name="reports/hotel/daily_checkouts.html"
    def get_context_data(self, **kwargs):
        c=super().get_context_data(**kwargs); form,qs=self.filtered_bookings(apply_date_filters=False); qs=filter_booking_dates(qs,form,"check_out"); c.update(form=form,bookings=qs.order_by("room__number")); return c


class ReservationReportView(HotelReportBase):
    template_name="reports/hotel/reservation_report.html"
    def get_context_data(self, **kwargs):
        c=super().get_context_data(**kwargs); form,qs=self.filtered_bookings(); c.update(form=form,bookings=qs.order_by("-created"),total_bookings=qs.count()); return c


class GuestHistoryReportView(HotelReportBase):
    template_name="reports/hotel/guest_history.html"
    def get_context_data(self, **kwargs):
        c=super().get_context_data(**kwargs); form,qs=self.filtered_bookings(); c.update(form=form,bookings=qs.order_by("-check_in"),total_bookings=qs.count()); return c


def stay_rows(bookings, start=None, end=None, today=None):
    """Return room-stay charges overlapping an inclusive report date range.

    RoomStay end_date is exclusive. User-facing report end_date is inclusive,
    so the report converts it to an exclusive boundary by adding one day.
    Open stays are counted through the current hotel date, consistent with the
    RoomStay.nights billing convention. No model data is changed.
    """
    today = today or timezone.localdate()
    report_start = start
    report_end_exclusive = (end + timedelta(days=1)) if end else (today + timedelta(days=1))
    stays = RoomStay.objects.filter(booking__in=bookings).select_related(
        "booking__guest", "booking", "room"
    ).order_by("-start_date", "room__number")
    if report_start:
        stays = stays.filter(Q(end_date__isnull=True) | Q(end_date__gt=report_start))
        stays = stays.filter(start_date__lt=report_end_exclusive)
    else:
        stays = stays.filter(start_date__lt=report_end_exclusive)
    rows = []
    total = Decimal("0.00")
    for stay in stays:
        effective_start = max(stay.start_date, report_start) if report_start else stay.start_date
        natural_end_exclusive = stay.end_date or (today + timedelta(days=1))
        effective_end = min(natural_end_exclusive, report_end_exclusive)
        nights = max((effective_end - effective_start).days, 0)
        amount = Decimal(nights) * stay.rate
        # Preserve the existing same-day checked-out billing fallback when
        # the selected range includes the stay's date and the ledger has zero nights.
        if (nights == 0 and stay.booking.status == "checked_out"
                and stay.end_date == stay.start_date
                and (report_start is None or stay.start_date >= report_start)
                and stay.start_date < report_end_exclusive):
            nights = 1
            amount = stay.rate
        rows.append({"stay": stay, "nights": nights, "amount": amount})
        total += amount
    return rows, total


def report_dates(form):
    if form.is_valid():
        return form.cleaned_data.get("start_date"), form.cleaned_data.get("end_date")
    return None, None




class RoomRevenueReportView(HotelReportBase):
    template_name = "reports/hotel/room_revenue.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        form, bookings = self.filtered_bookings(
            apply_date_filters=False
        )
        start_date, end_date = report_dates(form)

        if form.is_valid():
            rows, total = stay_rows(
                bookings,
                start=start_date,
                end=end_date,
            )
        else:
            rows, total = [], Decimal("0.00")

        context.update(
            form=form,
            report=rows,
            total_revenue=total,
        )
        return context


class StayLedgerReportView(HotelReportBase):
    template_name = "reports/hotel/stay_ledger.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        form, bookings = self.filtered_bookings(
            apply_date_filters=False
        )
        start_date, end_date = report_dates(form)

        if form.is_valid():
            rows, total = stay_rows(
                bookings,
                start=start_date,
                end=end_date,
            )
        else:
            rows, total = [], Decimal("0.00")

        context.update(
            form=form,
            rows=rows,
            total=total,
        )
        return context





class OccupancyReportView(HotelReportBase):
    template_name="reports/hotel/occupancy_report.html"
    def get_context_data(self, **kwargs):
        c=super().get_context_data(**kwargs); selected=self.request.GET.get("date") or str(timezone.localdate())
        from datetime import date
        try: selected=date.fromisoformat(selected)
        except ValueError: selected=timezone.localdate()
        occupied=RoomStay.objects.filter(start_date__lte=selected).filter(Q(end_date__isnull=True)|Q(end_date__gt=selected)).values("room").distinct().count(); total=Room.objects.count()
        c.update(selected_date=selected,total_rooms=total,occupied_rooms=occupied,vacant_rooms=max(total-occupied,0),occupancy_rate=(occupied/total*100) if total else 0,form=ReportFilterForm(self.request.GET or None)); return c


class RoomStatusReportView(HotelReportBase):
    status=None; template_name="reports/hotel/room_status.html"
    def get_context_data(self, **kwargs):
        c=super().get_context_data(**kwargs); rooms=Room.objects.all().order_by("number"); c["rooms"]=rooms.filter(status=self.status) if self.status else rooms; c["status_label"]=dict(Room.ROOM_STATUS).get(self.status,"All"); return c

class AvailableRoomsReportView(RoomStatusReportView): status="available"
class OccupiedRoomsReportView(RoomStatusReportView): status="occupied"
class RoomCleaningReportView(RoomStatusReportView): status="cleaning"

class MaintenanceReportView(HotelReportBase):
    template_name="reports/hotel/room_status.html"
    def get_context_data(self, **kwargs):
        c=super().get_context_data(**kwargs); c["rooms"]=Room.objects.filter(status__in=["maintenance","out_of_order"]).order_by("number"); c["status_label"]="Maintenance / Out of Order"; return c


class RoomTypeRevenueReportView(HotelReportBase):
    template_name="reports/hotel/room_type_revenue.html"
    def get_context_data(self, **kwargs):
        c=super().get_context_data(**kwargs); form,b=self.filtered_bookings(apply_date_filters=False); start,end=report_dates(form); rows,total=stay_rows(b,start,end) if form.is_valid() else ([],Decimal("0.00")); totals={}
        for r in rows: totals[r["stay"].room.room_type]=totals.get(r["stay"].room.room_type,Decimal("0.00"))+r["amount"]
        c.update(form=form,report=[{"room_type":k,"total":v} for k,v in totals.items()],grand_total=total); return c


class BillingReportBase(ReportBase):
    def payment_queryset(self):
        form,start,end=self.date_range(); qs=Payment.objects.select_related("invoice__booking__guest","received_by").order_by("-created")
        if start: qs=qs.filter(created__date__gte=start)
        if end: qs=qs.filter(created__date__lte=end)
        return form,qs

class DailyPaymentReportView(BillingReportBase):
    template_name="reports/billing/daily_payment.html"
    def get_context_data(self,**kwargs):
        c=super().get_context_data(**kwargs); form,qs=self.payment_queryset(); c.update(form=form,payments=qs,total=qs.aggregate(total=Sum("amount"))["total"] or 0); return c

class PaymentMethodReportView(BillingReportBase):
    template_name="reports/billing/payment_method.html"
    def get_context_data(self,**kwargs):
        c=super().get_context_data(**kwargs); form,qs=self.payment_queryset(); c.update(form=form,methods=qs.values("payment_method").annotate(total=Sum("amount")).order_by("-total")); return c

def invoice_paid_as_of(invoice, end=None):
    """Sum payments received on or before end; end=None means current total."""
    payments = invoice.payment_set.all()
    if end:
        payments = payments.filter(created__date__lte=end)
    return payments.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")


class InvoiceSummaryReportView(BillingReportBase):
    template_name="reports/billing/invoice_summary.html"

    def invoice_rows(self):
        form,start,end=self.date_range()
        qs=Invoice.objects.select_related("booking__guest","booking__room").order_by("-created")
        if start: qs=qs.filter(created__date__gte=start)
        if end: qs=qs.filter(created__date__lte=end)
        rows = []
        for invoice in qs.prefetch_related("payment_set"):
            paid = invoice_paid_as_of(invoice, end)
            balance = max(Decimal("0.00"), invoice.total - paid)
            rows.append({"invoice": invoice, "total": invoice.total, "paid": paid, "balance": balance})
        return form, rows

    def get_context_data(self,**kwargs):
        c=super().get_context_data(**kwargs)
        form,rows=self.invoice_rows()
        c.update(form=form,report=rows)
        return c

class OutstandingBalancesReportView(InvoiceSummaryReportView):
    template_name="reports/billing/outstanding_balances.html"
    def get_context_data(self,**kwargs):
        c=super().get_context_data(**kwargs)
        form,rows=self.invoice_rows()
        c.update(form=form,report=[r for r in rows if r["balance"] > 0])
        return c

class FullyPaidInvoicesReportView(InvoiceSummaryReportView):
    template_name="reports/billing/fully_paid.html"
    def get_context_data(self,**kwargs):
        c=super().get_context_data(**kwargs)
        form,rows=self.invoice_rows()
        c.update(form=form,report=[r for r in rows if r["balance"] <= 0])
        return c

class PartialPaymentsReportView(InvoiceSummaryReportView):
    template_name="reports/billing/partial_payments.html"
    def get_context_data(self,**kwargs):
        c=super().get_context_data(**kwargs)
        form,rows=self.invoice_rows()
        c.update(form=form,report=[r for r in rows if r["paid"] > 0 and r["balance"] > 0])
        return c

class ComponentPaidPendingReportView(BillingReportBase):
    component=""; template_name="reports/billing/component_paid_pending.html"
    def get_context_data(self,**kwargs):
        c=super().get_context_data(**kwargs); form,start,end=self.date_range(); rows=[]
        if self.component=="restaurant": qs=Order.objects.select_related("booking__guest","waiter"); paid_model=RestaurantPaymentAllocation; field="order"; total_field="total_amount"
        elif self.component=="service": qs=Service.objects.select_related("booking__guest"); paid_model=ServicePaymentAllocation; field="service"; total_field="total_amount"
        else: qs=Booking.objects.select_related("guest","room"); paid_model=RoomPaymentAllocation; field="booking"; total_field="room_total"
        if start: qs=qs.filter(**({"created_at__date__gte":start} if self.component=="restaurant" else {"created__date__gte":start}))
        if end: qs=qs.filter(**({"created_at__date__lte":end} if self.component=="restaurant" else {"created__date__lte":end}))
        for obj in qs:
            paid=paid_model.objects.filter(**{field:obj}).aggregate(total=Sum("amount"))["total"] or Decimal("0.00"); total=getattr(obj,total_field); rows.append({"object":obj,"total":total,"paid":paid,"pending":max(total-paid,Decimal("0.00"))})
        c.update(form=form,report=rows,component=self.component); return c
class RestaurantPaidPendingReportView(ComponentPaidPendingReportView): component="restaurant"
class ServicePaidPendingReportView(ComponentPaidPendingReportView): component="service"
class RoomPaidPendingReportView(ComponentPaidPendingReportView): component="room"


class RestaurantReportBase(ReportBase):
    def orders(self):
        form,start,end=self.date_range(); qs=Order.objects.select_related("waiter","employee","booking__guest").prefetch_related("items__food").order_by("-created_at")
        if start: qs=qs.filter(created_at__date__gte=start)
        if end: qs=qs.filter(created_at__date__lte=end)
        if form.is_valid():
            filters = {}
            if form.cleaned_data.get("waiter"):
                filters["waiter"] = form.cleaned_data["waiter"]
            # Apply category and food on the same related item join. The item-level
            # aggregation below repeats these filters to prevent order-level leakage.
            if form.cleaned_data.get("category"):
                filters["items__food__category"] = form.cleaned_data["category"]
            if form.cleaned_data.get("food"):
                filters["items__food"] = form.cleaned_data["food"]
            if filters:
                qs = qs.filter(**filters)
        return form,qs.distinct()





class DailyRestaurantSalesReportView(RestaurantReportBase):
    template_name = "reports/restaurant/daily_sales.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form, orders = self.orders()

        # Default: show each order's complete total.
        order_rows = []
        total_sales = Decimal("0.00")

        # If category or food is filtered, calculate matching item totals.
        use_item_totals = False
        if form.is_valid():
            use_item_totals = bool(
                form.cleaned_data.get("category")
                or form.cleaned_data.get("food")
            )

        if use_item_totals:
            items = filtered_restaurant_items(orders, form)

            # Aggregate each selected food's value per order.
            item_rows = (
                items.values("order_id")
                .annotate(
                    filtered_total=Sum(
                        F("quantity") * F("food__price")
                    )
                )
            )

            totals_by_order = {
                row["order_id"]: row["filtered_total"] or Decimal("0.00")
                for row in item_rows
            }

            for order in orders:
                amount = totals_by_order.get(
                    order.id, Decimal("0.00")
                )

                # Only show orders that contain the selected food/category.
                if order.id in totals_by_order:
                    order_rows.append({
                        "order": order,
                        "total": amount,
                    })
                    total_sales += amount

        else:
            # No food/category filter: use the complete order totals.
            for order in orders:
                amount = order.total_amount or Decimal("0.00")
                order_rows.append({
                    "order": order,
                    "total": amount,
                })
                total_sales += amount

        context.update(
            form=form,
            orders=orders,
            order_rows=order_rows,
            total_sales=total_sales,
        )
        return context


class MonthlySalesReportView(DailyRestaurantSalesReportView): template_name="reports/restaurant/monthly_sales.html"
class OrderHistoryReportView(DailyRestaurantSalesReportView): template_name="reports/restaurant/order_history.html"

class WaiterSalesReportView(RestaurantReportBase):
    template_name="reports/restaurant/waiter_sales.html"
    def get_context_data(self,**kwargs):
        c=super().get_context_data(**kwargs); form,qs=self.orders(); rows=qs.values("waiter__username").annotate(total_sales=Sum("total_amount"),total_orders=Count("id")).order_by("-total_sales"); c.update(form=form,report=rows); return c
class OrdersPerWaiterReportView(WaiterSalesReportView): template_name="reports/restaurant/orders_per_waiter.html"
class CollectionsPerWaiterReportView(ReportBase):
    template_name="reports/restaurant/collections_per_waiter.html"
    def get_context_data(self,**kwargs):
        c=super().get_context_data(**kwargs); form,start,end=self.date_range(); qs=Payment.objects.select_related("received_by");
        if start: qs=qs.filter(created__date__gte=start)
        if end: qs=qs.filter(created__date__lte=end)
        c.update(form=form,report=qs.values("received_by__username").annotate(total_collected=Sum("amount")).order_by("-total_collected")); return c
class UnpaidOrdersPerWaiterReportView(RestaurantReportBase):
    template_name="reports/restaurant/unpaid_orders_per_waiter.html"
    def get_context_data(self,**kwargs):
        c=super().get_context_data(**kwargs); form,qs=self.orders(); rows=[]
        for waiter_id in qs.values_list("waiter_id",flat=True).distinct():
            orders=qs.filter(waiter_id=waiter_id); pending=Decimal("0.00")
            for order in orders:
                paid=RestaurantPaymentAllocation.objects.filter(order=order).aggregate(total=Sum("amount"))["total"] or 0; pending += max(order.total_amount-paid,Decimal("0.00"))
            rows.append({"waiter":qs.filter(waiter_id=waiter_id).first().waiter,"unpaid_total":pending})
        c.update(form=form,report=rows); return c
def filtered_restaurant_items(orders, form):
    """Apply food/category filters to item rows, not only to their parent orders."""
    items = OrderItem.objects.filter(order__in=orders).select_related("food", "food__category")
    if form.is_valid():
        category = form.cleaned_data.get("category")
        food = form.cleaned_data.get("food")
        if category:
            items = items.filter(food__category=category)
        if food:
            items = items.filter(food=food)
    return items

'''
def top_selling_food_rows(orders, form):
    return filtered_restaurant_items(orders, form).values(
        "food_id", "food__name", "food__category__name"
    ).annotate(
        total_qty=Coalesce(Sum("quantity"), 0),
        sales=Coalesce(Sum(F("quantity") * F("food__price")), Decimal("0.00")),
    ).order_by("-total_qty", "food__name", "food_id")


def category_sales_rows(orders, form):
    return filtered_restaurant_items(orders, form).values(
        "food__category_id", "food__category__name"
    ).annotate(
        total_qty=Coalesce(Sum("quantity"), 0),
        total_sales=Coalesce(Sum(F("quantity") * F("food__price")), Decimal("0.00")),
    ).order_by("-total_sales", "food__category__name", "food__category_id")

'''


def filtered_restaurant_items(orders, form):
    """Apply category and food filters to the actual order-item rows."""
    items = OrderItem.objects.filter(
        order__in=orders
    ).select_related("food", "food__category")

    if form.is_valid():
        category = form.cleaned_data.get("category")
        food = form.cleaned_data.get("food")

        if category:
            items = items.filter(food__category=category)

        if food:
            items = items.filter(food=food)

    return items


def top_selling_food_rows(orders, form):
    return filtered_restaurant_items(orders, form).values(
        "food_id",
        "food__name",
        "food__category__name",
    ).annotate(
        total_qty=Coalesce(Sum("quantity"), 0),
        sales=Coalesce(
            Sum(F("quantity") * F("food__price")),
            Decimal("0.00"),
        ),
    ).order_by("-total_qty", "food__name", "food_id")


def category_sales_rows(orders, form):
    return filtered_restaurant_items(orders, form).values(
        "food__category_id",
        "food__category__name",
    ).annotate(
        total_qty=Coalesce(Sum("quantity"), 0),
        total_sales=Coalesce(
            Sum(F("quantity") * F("food__price")),
            Decimal("0.00"),
        ),
    ).order_by("-total_sales", "food__category__name", "food__category_id")






class TopSellingFoodsReportView(RestaurantReportBase):
    template_name = "reports/restaurant/top_selling_foods.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form, orders = self.orders()
        foods = top_selling_food_rows(orders, form)

        context.update(form=form, foods=foods)
        return context

'''
class CategorySalesReportView(RestaurantReportBase):
    template_name="reports/restaurant/category_sales.html"
    def get_context_data(self,**kwargs):
        c=super().get_context_data(**kwargs); form,qs=self.orders(); rows=category_sales_rows(qs,form); c.update(form=form,categories=rows); return c
'''


class CategorySalesReportView(RestaurantReportBase):
    template_name = "reports/restaurant/category_sales.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form, orders = self.orders()
        categories = category_sales_rows(orders, form)

        context.update(form=form, categories=categories)
        return context


class TableSalesReportView(RestaurantReportBase):
    template_name="reports/restaurant/table_sales.html"
    def get_context_data(self,**kwargs):
        c=super().get_context_data(**kwargs); form,qs=self.orders(); c.update(form=form,tables=qs.values("table_number").annotate(total_sales=Sum("total_amount"),total_orders=Count("id")).order_by("-total_sales")); return c


class PurchaseReportView(ReportBase):
    template_name="reports/purchases/purchase_report.html"
    def get_context_data(self,**kwargs):
        c=super().get_context_data(**kwargs); form,start,end=self.date_range(); qs=Purchase.objects.select_related("supplier","added_by").prefetch_related("items__item").order_by("-date","-id")
        if start: qs=qs.filter(date__gte=start)
        if end: qs=qs.filter(date__lte=end)
        if form.is_valid() and form.cleaned_data.get("supplier"):
            qs=qs.filter(supplier=form.cleaned_data["supplier"])
        c.update(form=form,purchases=qs,total=qs.aggregate(total=Sum("total_amount"))["total"] or 0); return c
class SupplierPurchaseReportView(PurchaseReportView): template_name="reports/purchases/supplier_purchase_report.html"
class LowStockReportView(ReportBase):
    template_name="reports/purchases/low_stock.html"
    def get_context_data(self,**kwargs): c=super().get_context_data(**kwargs); c["items"]=InventoryItem.objects.filter(current_stock__lte=F("reorder_level")).order_by("current_stock","name"); return c


class RestaurantSalesExcelView(ReportBase):
    def get(self, request, *args, **kwargs):
        form, orders = RestaurantReportBase.orders(self)
        wb = Workbook()
        ws = wb.active
        ws.title = "Restaurant Sales"
        ws.append(["Order", "Date", "Waiter", "Guest/Target", "Total"])
        for o in orders:
            target = f"Room {o.booking.room.number}" if o.booking else (f"Table {o.table_number}" if o.table_number else "Staff")
            ws.append([o.id, o.created_at.strftime("%Y-%m-%d %H:%M"), str(o.waiter or ""), target, float(o.total_amount)])
        response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = 'attachment; filename="restaurant_sales.xlsx"'
        wb.save(response)
        return response


class RestaurantSalesPDFView(ReportBase):
    def get(self, request, *args, **kwargs):
        _, orders = RestaurantReportBase.orders(self)
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = 'inline; filename="restaurant_sales.pdf"'
        pdf = canvas.Canvas(response)
        pdf.setTitle("Restaurant Sales")
        pdf.drawString(40, 800, "Restaurant Sales Report")
        y = 775
        for o in orders[:45]:
            target = f"Room {o.booking.room.number}" if o.booking else (f"Table {o.table_number}" if o.table_number else "Staff")
            pdf.drawString(40, y, f"#{o.id}  {o.created_at:%Y-%m-%d %H:%M}  {target}  ${o.total_amount:.2f}")
            y -= 16
            if y < 40:
                pdf.showPage(); y = 800
        pdf.save()
        return response

# ---------------------------------------------------------------------------
# Management financial statements
# ---------------------------------------------------------------------------
from finance.models import Expense, ExpenseCategory
from django.db.models.functions import TruncMonth


def _date_bounds(request):
    form = DateRangeForm(request.GET or None)
    if form.is_valid():
        return form, form.cleaned_data.get('start_date'), form.cleaned_data.get('end_date')
    return form, None, None


def _room_revenue_between(start, end):
    """Room-stay revenue for inclusive report dates using the same stay ledger."""
    _, total = stay_rows(Booking.objects.all(), start=start, end=end)
    return total


class FinancialReportBase(ReportBase):
    allowed_roles = MANAGEMENT_ROLES

    def financial_range(self):
        form, start, end = _date_bounds(self.request)
        today = timezone.localdate()
        if not form.is_valid():
            return form, today.replace(day=1), today
        if not start and not end:
            start, end = today.replace(day=1), today
        elif start and not end:
            end = today
        elif end and not start:
            start = end.replace(day=1)
        return form, start, end

    def _revenue(self, start, end):
        room = _room_revenue_between(start, end)
        orders = Order.objects.filter(created_at__date__gte=start, created_at__date__lte=end).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        services = Service.objects.filter(date__gte=start, date__lte=end).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        return {'room': room, 'restaurant': orders, 'services': services, 'total': room + orders + services}

    def _costs(self, start, end):
        purchases = Purchase.objects.filter(date__gte=start, date__lte=end).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        expenses = Expense.objects.filter(date__gte=start, date__lte=end).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        return {'purchases': purchases, 'expenses': expenses, 'total': purchases + expenses}


class FinancialDashboardView(FinancialReportBase):
    template_name = 'reports/financial/dashboard.html'

    def get_context_data(self, **kwargs):
        c = super().get_context_data(**kwargs)
        form, start, end = self.financial_range()
        from accounting.services import get_operational_receivables_as_of, get_profit_loss_statement
        pnl = get_profit_loss_statement(start, end)

        revenue = {
            'room': pnl['revenue'].get('4000', Decimal('0.00')),
            'restaurant': pnl['revenue'].get('4100', Decimal('0.00')),
            'services': pnl['revenue'].get('4200', Decimal('0.00')),
            'discounts': pnl['revenue'].get('4900', Decimal('0.00')),
            'total': pnl['total_revenue'],
        }
        costs = {
            'purchases': pnl['purchase_cogs'],
            'cogs': pnl['cogs'],
            'expenses': pnl['total_expenses'],
            'total': pnl['cogs'] + pnl['total_expenses'],
        }
        cash_summary = cash_flow_summary(start, end)
        collections = cash_summary['collections']
        cash_out = cash_summary['operating_outflow']
        receivables = get_operational_receivables_as_of(end)
        c.update(
            form=form, start=start, end=end, revenue=revenue, costs=costs,
            collections=collections, cash_out=cash_out, net_cash=collections-cash_out,
            profit=pnl['net_profit'], receivables=receivables,
            cogs=pnl['cogs'], cogs_source=pnl['cogs_source'],
            gross_profit=pnl['gross_profit'], operating_profit=pnl['operating_profit'],
            total_expenses=pnl['total_expenses'], net_profit=pnl['net_profit'],
        )
        return c


class ProfitLossReportView(FinancialReportBase):
    template_name = 'reports/financial/profit_loss.html'

    def get_context_data(self, **kwargs):
        c = super().get_context_data(**kwargs)
        form, start, end = self.financial_range()
        from accounting.services import get_profit_loss_statement
        pnl = get_profit_loss_statement(start, end)
        expense_rows = Expense.objects.filter(
            date__gte=start, date__lte=end
        ).values('category__name').annotate(total=Sum('amount')).order_by('-total')
        c.update(
            form=form, start=start, end=end,
            revenue={
                'room': pnl['revenue'].get('4000', Decimal('0.00')),
                'restaurant': pnl['revenue'].get('4100', Decimal('0.00')),
                'services': pnl['revenue'].get('4200', Decimal('0.00')),
                'discounts': pnl['revenue'].get('4900', Decimal('0.00')),
                'total': pnl['total_revenue'],
            },
            costs={'purchases': pnl['purchase_cogs'], 'cogs': pnl['cogs'], 'expenses': pnl['total_expenses'],
                   'total': pnl['cogs'] + pnl['total_expenses']},
            cogs=pnl['cogs'], cogs_source=pnl['cogs_source'],
            gross_profit=pnl['gross_profit'], gross_result=pnl['gross_profit'],
            operating_profit=pnl['operating_profit'], net_profit=pnl['net_profit'],
            margin=(pnl['net_profit'] / pnl['total_revenue'] * 100) if pnl['total_revenue'] else Decimal('0.00'),
            gross_margin=(pnl['gross_profit'] / pnl['total_revenue'] * 100) if pnl['total_revenue'] else Decimal('0.00'),
            operating_margin=(pnl['operating_profit'] / pnl['total_revenue'] * 100) if pnl['total_revenue'] else Decimal('0.00'),
            expense_rows=expense_rows, accounting_expense_rows=pnl['expense_rows'],
        )
        return c


def cash_flow_summary(start, end):
    """Summarize recorded cash movements, not accrual purchases or COGS.

    Customer payments, supplier payments, and expenses each carry a recorded
    payment method/date. Purchase orders alone are not cash disbursements.
    Opening balances, transfers, refunds, and unrecorded payments are outside
    the current data model and therefore excluded.
    """
    from accounting.models import SupplierPayment
    collections = Payment.objects.filter(
        created__date__gte=start, created__date__lte=end
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    supplier_payments = SupplierPayment.objects.filter(
        date__gte=start, date__lte=end
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    expenses = Expense.objects.filter(
        date__gte=start, date__lte=end
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    return {
        "collections": collections,
        "supplier_payments": supplier_payments,
        "expenses": expenses,
        "operating_outflow": supplier_payments + expenses,
        "net_cash": collections - supplier_payments - expenses,
    }


class CashFlowReportView(FinancialReportBase):
    template_name = 'reports/financial/cash_flow.html'

    def get_context_data(self, **kwargs):
        c = super().get_context_data(**kwargs)
        form, start, end = self.financial_range()
        c.update(form=form, start=start, end=end, **cash_flow_summary(start, end))
        return c


class ReceivablesReportView(FinancialReportBase):
    template_name = 'reports/financial/receivables.html'

    def get_context_data(self, **kwargs):
        c = super().get_context_data(**kwargs)
        form, start, end = self.financial_range()
        from collections import OrderedDict
        from billing.services import get_booking_totals

        invoices = (
            Invoice.objects
            .select_related('booking__guest', 'booking__room')
            .prefetch_related('payment_set')
            .filter(created__date__lte=end)
            .order_by('booking__guest__first_name', 'booking__guest__last_name', '-created')
        )

        customer_map = OrderedDict()
        invoice_rows = []
        for invoice in invoices:
            totals = get_booking_totals(invoice.booking, as_of=end, include_checkout_night=False)
            total = max(
                Decimal('0.00'),
                totals['room_total'] + totals['restaurant_total'] +
                totals['service_total'] - (invoice.discount or Decimal('0.00')),
            )
            paid = sum(
                (p.amount for p in invoice.payment_set.all()
                 if p.created and p.created.date() <= end),
                Decimal('0.00'),
            )
            balance = max(Decimal('0.00'), total - paid)
            if balance <= 0:
                continue

            guest = invoice.booking.guest
            key = guest.pk
            customer_map.setdefault(key, {
                'guest': guest, 'invoice_count': 0, 'total': Decimal('0.00'),
                'paid': Decimal('0.00'), 'balance': Decimal('0.00'), 'invoices': []
            })
            row = {'invoice': invoice, 'total': total, 'paid': paid, 'balance': balance}
            customer_map[key]['invoice_count'] += 1
            customer_map[key]['total'] += total
            customer_map[key]['paid'] += paid
            customer_map[key]['balance'] += balance
            customer_map[key]['invoices'].append(row)
            invoice_rows.append(row)

        customer_rows = sorted(customer_map.values(), key=lambda r: (-r['balance'], str(r['guest'])))
        total_billed = sum((r['total'] for r in customer_rows), Decimal('0.00'))
        total_paid = sum((r['paid'] for r in customer_rows), Decimal('0.00'))
        total_outstanding = sum((r['balance'] for r in customer_rows), Decimal('0.00'))
        c.update(form=form, start=start, end=end, report=invoice_rows, customer_rows=customer_rows,
                 total_billed=total_billed, total_paid=total_paid, total_outstanding=total_outstanding)
        return c


class ExpenseReportView(FinancialReportBase):
    template_name = 'reports/financial/expense_report.html'

    def get_context_data(self, **kwargs):
        c = super().get_context_data(**kwargs)
        form, start, end = self.financial_range()
        qs = Expense.objects.select_related('category', 'created_by').filter(date__gte=start, date__lte=end)
        c.update(form=form, start=start, end=end, expenses=qs,
                 total=qs.aggregate(total=Sum('amount'))['total'] or Decimal('0.00'))
        return c
