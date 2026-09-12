from decimal import Decimal
from datetime import date, datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Sum, F, Value, DecimalField, OuterRef, Subquery, Case, When
from django.db.models.functions import Coalesce
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import get_template
from django.urls import reverse_lazy
from django.views.generic import TemplateView, UpdateView
from xhtml2pdf import pisa

from accounts.mixins import RoleRequiredMixin
from hotel.models import Booking
from .filters import InvoiceFilter
from .forms import PaymentForm
from .models import Invoice, Payment
from .services import get_financial_summary, get_paid_total, sync_invoice
from .utils import allocate_payment, rebuild_allocations

ROLES = ["admin", "manager", "reception"]


class InvoiceDetailView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    allowed_roles = ROLES
    template_name = "billing/invoice.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        invoice = get_object_or_404(
            Invoice.objects.select_related("booking", "booking__guest", "booking__room"),
            pk=self.kwargs["pk"],
        )
        booking = invoice.booking
        # Invoice and Booking always read the same ledger/source data.
        if booking.status != "checked_out":
            sync_invoice(booking, rebuild_payment_allocations=True)
            invoice.refresh_from_db()
        summary = get_financial_summary(
            booking,
            as_of=booking.check_out or date.today(),
            include_checkout_night=booking.status == "checked_out",
        )
        context.update({
            "invoice": invoice,
            "booking": booking,
            "summary": summary,
            "room_stays": booking.stays,
            "orders": booking.orders.select_related("waiter", "employee").prefetch_related("items__food"),
            "services": booking.services.all().order_by("date", "id"),
            "payments": invoice.payment_set.select_related("received_by").order_by("created", "id"),
        })
        return context


class BookingPaymentSummaryView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    template_name = "billing/booking_payment_summary.html"
    allowed_roles = ROLES

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        summary = []
        for booking in Booking.objects.filter(status__in=["reserved", "checked_in", "checked_out"]).select_related("guest", "room"):
            if booking.status == "reserved":
                continue
            invoice = Invoice.objects.filter(booking=booking).first() or sync_invoice(booking)
            data = get_financial_summary(
                booking,
                as_of=booking.check_out or date.today(),
                include_checkout_night=booking.status == "checked_out",
            )
            summary.append({"booking": booking, **data})
        context["summary"] = summary
        return context


class Invoice_ListView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    allowed_roles = ROLES
    template_name = "billing/invoice_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payment_subquery = Payment.objects.filter(invoice=OuterRef("pk")).values("invoice").annotate(
            total=Sum("amount")
        ).values("total")
        queryset = Invoice.objects.select_related("booking", "booking__guest", "booking__room").annotate(
            paid_total=Coalesce(
                Subquery(payment_subquery),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=10, decimal_places=2),
            ),
        ).annotate(
            balance=F("total") - F("paid_total"),
        ).annotate(
            payment_status=Case(
                When(balance__lte=0, then=Value("paid")),
                When(paid_total=0, then=Value("unpaid")),
                default=Value("partial"),
            )
        ).order_by("-created", "-id")
        invoice_filter = InvoiceFilter(self.request.GET, queryset=queryset)
        filtered = invoice_filter.qs
        context["filter"] = invoice_filter
        context["active_invoices"] = filtered.filter(booking__status__in=["reserved", "checked_in"])
        context["completed_invoices"] = filtered.filter(booking__status="checked_out")
        return context


class PaymentView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    allowed_roles = ROLES
    template_name = "billing/payment.html"

    def get_booking(self):
        return get_object_or_404(Booking.objects.select_related("guest", "room"), pk=self.kwargs["pk"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        booking = self.get_booking()
        invoice = Invoice.objects.filter(booking=booking).first() or sync_invoice(booking)
        summary = get_financial_summary(booking, as_of=booking.check_out or date.today(), include_checkout_night=booking.status == "checked_out")
        context.update({
            "booking": booking,
            "invoice": invoice,
            "summary": summary,
            "payments": invoice.payment_set.select_related("received_by").order_by("created", "id"),
            "form": PaymentForm(),
        })
        return context

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        booking = self.get_booking()
        invoice = Invoice.objects.select_for_update().filter(booking=booking).first()
        if not invoice:
            invoice = sync_invoice(booking)
        form = PaymentForm(request.POST)
        if not form.is_valid():
            context = self.get_context_data()
            context["form"] = form
            return self.render_to_response(context)

        amount = form.cleaned_data["amount"]
        paid = get_paid_total(invoice)
        balance = max(Decimal("0.00"), invoice.total - paid)
        if amount > balance:
            form.add_error("amount", f"Payment cannot exceed the outstanding balance of ${balance:,.2f}.")
            context = self.get_context_data()
            context["form"] = form
            return self.render_to_response(context)

        payment = Payment.objects.create(
            invoice=invoice,
            amount=amount,
            payment_method=form.cleaned_data["payment_method"],
            received_by=request.user,
        )
        allocate_payment(invoice, payment)
        messages.success(request, f"Payment of ${amount:,.2f} recorded successfully.")
        return redirect("payment", pk=booking.pk)


class PaymentUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    allowed_roles = ["admin", "manager"]
    model = Payment
    fields = ["amount", "payment_method"]
    template_name = "billing/payment_update.html"

    @transaction.atomic
    def form_valid(self, form):
        payment = self.get_object()
        invoice = payment.invoice
        new_amount = form.cleaned_data["amount"]
        other_paid = get_paid_total(invoice) - payment.amount
        if new_amount > max(Decimal("0.00"), invoice.total - other_paid):
            form.add_error("amount", "The payment would exceed the invoice balance.")
            return self.form_invalid(form)
        response = super().form_valid(form)
        rebuild_allocations(invoice)
        return response

    def get_success_url(self):
        return reverse_lazy("payment", kwargs={"pk": self.object.invoice.booking_id})


class PaymentReceiptView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    template_name = "billing/payment_receipt.html"
    allowed_roles = ROLES

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        booking = get_object_or_404(Booking, pk=self.kwargs["pk"])
        invoice = get_object_or_404(Invoice, booking=booking)
        context.update({
            "booking": booking,
            "invoice": invoice,
            "payments": invoice.payment_set.all().order_by("created", "id"),
            "paid_total": get_paid_total(invoice),
            "balance": invoice.balance,
        })
        return context


@login_required
def payment_receipt_pdf(request, pk):
    if getattr(getattr(request.user, "userprofile", None), "role", None) not in ROLES:
        return HttpResponseForbidden("<h1>You are not allowed to access this receipt.</h1>")
    booking = get_object_or_404(Booking, pk=pk)
    invoice = get_object_or_404(Invoice, booking=booking)
    payments = invoice.payment_set.all().order_by("created", "id")
    context = {
        "booking": booking,
        "invoice": invoice,
        "payments": payments,
        "paid_total": get_paid_total(invoice),
        "balance": invoice.balance,
        "logo_url": request.build_absolute_uri("/static/images/logo.png"),
    }
    html = get_template("billing/payment_receipt_pdf1.html").render(context)
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="receipt_{booking.id}.pdf"'
    pisa.CreatePDF(html, dest=response)
    return response


class RevenueView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    allowed_roles = ["admin", "manager"]
    template_name = "dashboard/revenue.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        value = self.request.GET.get("date")
        try:
            rev_date = datetime.strptime(value, "%Y-%m-%d").date() if value else date.today()
        except ValueError:
            rev_date = date.today()
        context["revenue_date"] = rev_date
        context["revenue"] = Invoice.objects.filter(created__date=rev_date).aggregate(total=Sum("total"))["total"] or Decimal("0.00")
        return context
