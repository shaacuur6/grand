from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, F, Q, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import render
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
    def filtered_bookings(self):
        form = ReportFilterForm(self.request.GET or None)
        qs = Booking.objects.select_related("guest", "room").prefetch_related("room_stays")
        if form.is_valid():
            d = form.cleaned_data
            if d.get("start_date"): qs = qs.filter(check_in__gte=d["start_date"])
            if d.get("end_date"): qs = qs.filter(check_in__lte=d["end_date"])
            if d.get("room"): qs = qs.filter(room=d["room"])
            if d.get("room_type"): qs = qs.filter(room__room_type=d["room_type"])
            if d.get("guest"): qs = qs.filter(guest=d["guest"])
            if d.get("status"): qs = qs.filter(status=d["status"])
            if d.get("search"):
                term=d["search"]; search_q=Q(guest__first_name__icontains=term)|Q(guest__last_name__icontains=term)|Q(guest__phone__icontains=term)
                if term.isdigit(): search_q |= Q(room__number=int(term))
                qs=qs.filter(search_q)
        return form, qs.distinct()


class DailyCheckInsReportView(HotelReportBase):
    template_name="reports/hotel/daily_checkins.html"
    def get_context_data(self, **kwargs):
        c=super().get_context_data(**kwargs); form,qs=self.filtered_bookings(); day=self.request.GET.get("start_date") or str(timezone.localdate()); qs=qs.filter(check_in=day); c.update(form=form,bookings=qs.order_by("room__number")); return c


class DailyCheckOutsReportView(HotelReportBase):
    template_name="reports/hotel/daily_checkouts.html"
    def get_context_data(self, **kwargs):
        c=super().get_context_data(**kwargs); form,qs=self.filtered_bookings(); day=self.request.GET.get("end_date") or str(timezone.localdate()); qs=qs.filter(check_out=day); c.update(form=form,bookings=qs.order_by("room__number")); return c


class ReservationReportView(HotelReportBase):
    template_name="reports/hotel/reservation_report.html"
    def get_context_data(self, **kwargs):
        c=super().get_context_data(**kwargs); form,qs=self.filtered_bookings(); c.update(form=form,bookings=qs.order_by("-created"),total_bookings=qs.count()); return c


class GuestHistoryReportView(HotelReportBase):
    template_name="reports/hotel/guest_history.html"
    def get_context_data(self, **kwargs):
        c=super().get_context_data(**kwargs); form,qs=self.filtered_bookings(); c.update(form=form,bookings=qs.order_by("-check_in"),total_bookings=qs.count()); return c


def stay_rows(bookings):
    rows=[]; total=Decimal("0.00"); today=timezone.localdate()
    stays=RoomStay.objects.filter(booking__in=bookings).select_related("booking__guest","room").order_by("-start_date","room__number")
    for stay in stays:
        end=stay.end_date or today; nights=max((end-stay.start_date).days,0); amount=Decimal(nights)*stay.rate
        rows.append({"stay":stay,"nights":nights,"amount":amount}); total += amount
    return rows,total


class RoomRevenueReportView(HotelReportBase):
    template_name="reports/hotel/room_revenue.html"
    def get_context_data(self, **kwargs):
        c=super().get_context_data(**kwargs); form,b=self.filtered_bookings(); rows,total=stay_rows(b); c.update(form=form,report=rows,total_revenue=total); return c


class StayLedgerReportView(HotelReportBase):
    template_name="reports/hotel/stay_ledger.html"
    def get_context_data(self, **kwargs):
        c=super().get_context_data(**kwargs); form,b=self.filtered_bookings(); rows,total=stay_rows(b); c.update(form=form,rows=rows,total=total); return c


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
        c=super().get_context_data(**kwargs); form,b=self.filtered_bookings(); rows,total=stay_rows(b); totals={}
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

class InvoiceSummaryReportView(BillingReportBase):
    template_name="reports/billing/invoice_summary.html"

    def invoice_rows(self):
        form,start,end=self.date_range()
        qs=Invoice.objects.select_related("booking__guest","booking__room").order_by("-created")
        if start: qs=qs.filter(created__date__gte=start)
        if end: qs=qs.filter(created__date__lte=end)
        rows=[{"invoice":i,"total":i.total,"paid":i.paid_total,"balance":i.balance} for i in qs]
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
            if form.cleaned_data.get("waiter"):
                qs=qs.filter(waiter=form.cleaned_data["waiter"])
            if form.cleaned_data.get("category"):
                qs=qs.filter(items__food__category=form.cleaned_data["category"])
            if form.cleaned_data.get("food"):
                qs=qs.filter(items__food=form.cleaned_data["food"])
        return form,qs.distinct()

class DailyRestaurantSalesReportView(RestaurantReportBase):
    template_name="reports/restaurant/daily_sales.html"
    def get_context_data(self,**kwargs):
        c=super().get_context_data(**kwargs); form,qs=self.orders(); c.update(form=form,orders=qs,total_sales=qs.aggregate(total=Sum("total_amount"))["total"] or 0); return c
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
class TopSellingFoodsReportView(RestaurantReportBase):
    template_name="reports/restaurant/top_selling_foods.html"
    def get_context_data(self,**kwargs):
        c=super().get_context_data(**kwargs); form,qs=self.orders(); items=OrderItem.objects.filter(order__in=qs); rows=items.values("food__name").annotate(total_qty=Sum("quantity"),sales=Sum(F("quantity")*F("food__price"))).order_by("-total_qty"); c.update(form=form,foods=rows); return c
class CategorySalesReportView(RestaurantReportBase):
    template_name="reports/restaurant/category_sales.html"
    def get_context_data(self,**kwargs):
        c=super().get_context_data(**kwargs); form,qs=self.orders(); items=OrderItem.objects.filter(order__in=qs); rows=items.values("food__category__name").annotate(total_qty=Sum("quantity"),total_sales=Sum(F("quantity")*F("food__price"))).order_by("-total_sales"); c.update(form=form,categories=rows); return c
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
