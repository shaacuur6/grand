from datetime import date, datetime
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Sum, OuterRef, Subquery, Value, DecimalField, F, Case, When,CharField
from django.db.models.functions import Coalesce
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import get_template
from django.urls import reverse_lazy
from django.views.generic import DeleteView, ListView, TemplateView, UpdateView
from django.utils import timezone
from xhtml2pdf import pisa

from accounts.constants import BILLING_ROLES, MANAGEMENT_ROLES
from accounts.mixins import RoleRequiredMixin
from hotel.models import Booking
from .filters import InvoiceFilter
from .forms import InvoiceFilterForm, PaymentForm
from .models import Invoice, Payment
from .services import get_financial_summary, get_paid_total, sync_invoice
from .utils import allocate_payment, rebuild_allocations


class InvoiceListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    allowed_roles = BILLING_ROLES
    model = Invoice
    template_name = "billing/invoice_list.html"
    context_object_name = "invoices"
    paginate_by = 25

    def get_queryset(self):
        payment_subquery = (
            Payment.objects
            .filter(invoice=OuterRef("pk"))
            .values("invoice")
            .annotate(total_paid=Sum("amount"))
            .values("total_paid")
        )

        queryset = (
            Invoice.objects
            .select_related(
                "booking",
                "booking__guest",
                "booking__room",
            )
            .annotate(
                calculated_paid_total=Coalesce(
                    Subquery(payment_subquery),
                    Value(Decimal("0.00")),
                    output_field=DecimalField(
                        max_digits=10,
                        decimal_places=2,
                    ),
                )
            )
            .annotate(
                calculated_balance=F("total") - F("calculated_paid_total")
            )
            .annotate(
                calculated_payment_status=Case(
                    When(
                        calculated_balance__lte=0,
                        then=Value("paid"),
                    ),
                    When(
                        calculated_paid_total=0,
                        then=Value("unpaid"),
                    ),
                    default=Value("partial"),
                    output_field=CharField(),
                )
            )
            .order_by("-created")
        )

        return InvoiceFilter(
            self.request.GET,
            queryset=queryset,
        ).qs

# Backward-compatible name used by existing templates/urls.
#Invoice_ListView = InvoiceListView


class InvoiceDetailView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    allowed_roles = BILLING_ROLES
    template_name = "billing/invoice.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        invoice = get_object_or_404(Invoice.objects.select_related("booking", "booking__guest", "booking__room"), pk=self.kwargs["pk"])
        booking = invoice.booking
        if booking.status != "checked_out":
            sync_invoice(booking, rebuild_payment_allocations=True)
            invoice.refresh_from_db()
        summary = get_financial_summary(booking, as_of=booking.check_out or timezone.localdate(),
                                        include_checkout_night=booking.status == "checked_out")
        context.update({
            "invoice": invoice, "booking": booking, "summary": summary,
            "room_stays": booking.stays,
            "orders": booking.orders.select_related("waiter", "employee").prefetch_related("items__food"),
            "services": booking.services.all().order_by("date", "id"),
            "payments": invoice.payment_set.select_related("received_by").order_by("created", "id"),
        })
        return context


class InvoiceUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    allowed_roles = MANAGEMENT_ROLES
    model = Invoice
    fields = ["discount"]
    template_name = "billing/invoice_discount_form.html"
    success_url = reverse_lazy("invoice_list")

    def form_valid(self, form):
        form.instance.discount = max(form.cleaned_data["discount"], Decimal("0.00"))
        response = super().form_valid(form)
        rebuild_allocations(self.object)
        messages.success(self.request, "Invoice discount updated.")
        return response


class PaymentSummaryView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    allowed_roles = BILLING_ROLES
    template_name = "billing/booking_payment_summary.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        rows = []
        bookings = Booking.objects.filter(status__in=["checked_in", "checked_out"]).select_related("guest", "room")
        for booking in bookings:
            invoice = Invoice.objects.filter(booking=booking).first() or sync_invoice(booking)
            summary = get_financial_summary(booking, as_of=booking.check_out or timezone.localdate(),
                                            include_checkout_night=booking.status == "checked_out")
            rows.append({"booking": booking, **summary})
        context["summary"] = rows
        return context


class PaymentView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    allowed_roles = BILLING_ROLES
    template_name = "billing/payment.html"

    def get_booking(self):
        return get_object_or_404(Booking.objects.select_related("guest", "room"), pk=self.kwargs["pk"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        booking = self.get_booking()
        invoice = Invoice.objects.filter(booking=booking).first() or sync_invoice(booking)
        if booking.status != "checked_out":
            sync_invoice(booking)
            invoice.refresh_from_db()
        context.update({
            "booking": booking, "invoice": invoice,
            "summary": get_financial_summary(booking, as_of=booking.check_out or timezone.localdate(),
                                              include_checkout_night=booking.status == "checked_out"),
            "payments": invoice.payment_set.select_related("received_by").order_by("-created", "-id"),
            "form": PaymentForm(),
        })
        return context

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        booking = self.get_booking()
        sync_invoice(booking, include_checkout_night=booking.status == "checked_out")
        invoice = Invoice.objects.select_for_update().get(booking=booking)
        form = PaymentForm(request.POST)
        if not form.is_valid():
            context = self.get_context_data()
            context["form"] = form
            return self.render_to_response(context)
        amount = form.cleaned_data["amount"]
        balance = max(Decimal("0.00"), invoice.total - get_paid_total(invoice))
        if amount > balance:
            form.add_error("amount", f"Payment cannot exceed the outstanding balance of ${balance:,.2f}.")
            context = self.get_context_data()
            context["form"] = form
            return self.render_to_response(context)
        payment = Payment.objects.create(invoice=invoice, amount=amount,
                                         payment_method=form.cleaned_data["payment_method"],
                                         received_by=request.user)
        allocate_payment(invoice, payment)
        messages.success(request, f"Payment of ${amount:,.2f} recorded successfully.")
        return redirect("payment", pk=booking.pk)


class PaymentListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    allowed_roles = BILLING_ROLES
    model = Payment
    template_name = "billing/payment_list.html"
    context_object_name = "payments"

    def get_queryset(self):
        return Payment.objects.select_related("invoice__booking__guest", "received_by").order_by("-created", "-id")


class PaymentUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    allowed_roles = MANAGEMENT_ROLES
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
        messages.success(self.request, "Payment updated successfully.")
        return response

    def get_success_url(self):
        return reverse_lazy("payment", kwargs={"pk": self.object.invoice.booking_id})


class PaymentDeleteView(LoginRequiredMixin, RoleRequiredMixin, DeleteView):
    allowed_roles = MANAGEMENT_ROLES
    model = Payment
    template_name = "billing/payment_confirm_delete.html"

    def get_success_url(self):
        return reverse_lazy("payment", kwargs={"pk": self.object.invoice.booking_id})

    @transaction.atomic
    def form_valid(self, form):
        invoice = self.object.invoice
        response = super().form_valid(form)
        rebuild_allocations(invoice)
        messages.success(self.request, "Payment deleted successfully.")
        return response


class PaymentReceiptView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    allowed_roles = BILLING_ROLES
    template_name = "billing/payment_receipt.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        booking = get_object_or_404(Booking, pk=self.kwargs["pk"])
        invoice = get_object_or_404(Invoice, booking=booking)
        context.update({"booking": booking, "invoice": invoice,
                        "payments": invoice.payment_set.all().order_by("created", "id"),
                        "paid_total": get_paid_total(invoice), "balance": invoice.balance})
        return context


def payment_receipt_pdf(request, pk):
    profile = getattr(request.user, "userprofile", None)
    if not request.user.is_authenticated or profile is None or profile.role not in BILLING_ROLES:
        return HttpResponseForbidden("<h1>You are not allowed to access this receipt.</h1>")
    booking = get_object_or_404(Booking, pk=pk)
    invoice = get_object_or_404(Invoice, booking=booking)
    context = {"booking": booking, "invoice": invoice,
               "payments": invoice.payment_set.all().order_by("created", "id"),
               "paid_total": get_paid_total(invoice), "balance": invoice.balance,
               "logo_url": request.build_absolute_uri("/static/images/logo.png")}
    html = get_template("billing/payment_receipt_pdf1.html").render(context, request=request)
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="receipt_{booking.id}.pdf"'
    pisa.CreatePDF(html, dest=response)
    return response


class RevenueView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    allowed_roles = MANAGEMENT_ROLES
    template_name = "dashboard/revenue.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        value = self.request.GET.get("date")
        try:
            rev_date = datetime.strptime(value, "%Y-%m-%d").date() if value else timezone.localdate()
        except ValueError:
            rev_date = timezone.localdate()
        payments = Payment.objects.filter(created__date=rev_date)
        collections = payments.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        context.update({"revenue_date": rev_date, "revenue": collections, "payments": payments})
        return context
