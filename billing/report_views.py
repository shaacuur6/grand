from billing.models import (
    RestaurantPaymentAllocation,
    ServicePaymentAllocation,
    RoomPaymentAllocation
)




from django.views.generic import TemplateView
from django.db.models import Sum
from django.utils import timezone

from billing.models import Payment, Invoice
from restaurant.models import Order
from hotel.models import Service, Booking


class DailyPaymentReportView(TemplateView):

    template_name = "reports/billing/daily_payment.html"

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        today = timezone.now().date()

        payments = Payment.objects.filter(
            created__date=today
        )

        total = payments.aggregate(
            total=Sum("amount")
        )["total"] or 0

        context["payments"] = payments
        context["total"] = total

        return context
    



class OutstandingBalancesReportView(TemplateView):

    template_name = "reports/billing/outstanding_balances.html"

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        report = []

        invoices = Invoice.objects.all()

        for invoice in invoices:

            paid = Payment.objects.filter(
                invoice=invoice
            ).aggregate(
                total=Sum("amount")
            )["total"] or 0

            balance = invoice.total - paid

            if balance > 0:

                report.append({

                    "invoice": invoice,
                    "paid": paid,
                    "balance": balance

                })

        context["report"] = report
        return context
    



class FullyPaidInvoicesReportView(TemplateView):

    template_name = "reports/billing/fully_paid.html"

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        report = []

        invoices = Invoice.objects.all()

        for invoice in invoices:

            paid = Payment.objects.filter(
                invoice=invoice
            ).aggregate(
                total=Sum("amount")
            )["total"] or 0

            balance = invoice.total - paid

            if balance <= 0:

                report.append({

                    "invoice": invoice,
                    "paid": paid

                })

        context["report"] = report

        return context
    




class PartialPaymentsReportView(TemplateView):

    template_name = "reports/billing/partial_payments.html"

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        report = []

        invoices = Invoice.objects.all()

        for invoice in invoices:

            paid = Payment.objects.filter(
                invoice=invoice
            ).aggregate(
                total=Sum("amount")
            )["total"] or 0

            balance = invoice.total - paid

            if paid > 0 and balance > 0:

                report.append({

                    "invoice": invoice,
                    "paid": paid,
                    "balance": balance

                })

        context["report"] = report

        return context




from django.db.models import Sum

class PaymentMethodReportView(TemplateView):

    template_name = "reports/billing/payment_method.html"

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        methods = Payment.objects.values(
            "payment_method"
        ).annotate(

            total=Sum("amount")

        ).order_by("-total")

        context["methods"] = methods

        return context
    




class InvoiceSummaryReportView(TemplateView):

    template_name = "reports/billing/invoice_summary.html"

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        report = []

        invoices = Invoice.objects.all()

        for invoice in invoices:

            paid = Payment.objects.filter(
                invoice=invoice
            ).aggregate(
                total=Sum("amount")
            )["total"] or 0

            balance = invoice.total - paid

            report.append({

                "invoice": invoice,
                "total": invoice.total,
                "paid": paid,
                "balance": balance

            })

        context["report"] = report

        return context
    

# =========================================
# RESTAURANT PAID VS PENDING
# =========================================


class RestaurantPaidPendingReportView(TemplateView):

    template_name = (
        "reports/billing/restaurant_paid_pending.html"
    )

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        report = []

        orders = Order.objects.all().order_by("-id")

        for order in orders:

            paid = (
                RestaurantPaymentAllocation.objects
                .filter(order=order)
                .aggregate(total=Sum("amount"))
            )["total"] or 0

            pending = order.total_amount - paid

            report.append({

                "order": order,
                "total": order.total_amount,
                "paid": paid,
                "pending": pending

            })

        context["report"] = report

        return context


# =========================================
# SERVICE PAID VS PENDING
# =========================================

class ServicePaidPendingReportView(TemplateView):

    template_name = (
        "reports/billing/service_paid_pending.html"
    )

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        report = []

        services = Service.objects.all().order_by("-id")

        for service in services:

            paid = (
                ServicePaymentAllocation.objects
                .filter(service=service)
                .aggregate(total=Sum("amount"))
            )["total"] or 0

            pending = service.total_amount - paid

            report.append({

                "service": service,
                "total": service.total_amount,
                "paid": paid,
                "pending": pending

            })

        context["report"] = report

        return context


# =========================================
# ROOM PAID VS PENDING
# =========================================

class RoomPaidPendingReportView(TemplateView):

    template_name = (
        "reports/billing/room_paid_pending.html"
    )

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        report = []

        bookings = Booking.objects.all().order_by("-id")

        for booking in bookings:

            paid = (
                RoomPaymentAllocation.objects
                .filter(booking=booking)
                .aggregate(total=Sum("amount"))
            )["total"] or 0

            room_total = booking.room_total

            pending = room_total - paid

            report.append({

                "booking": booking,
                "total": room_total,
                "paid": paid,
                "pending": pending

            })

        context["report"] = report

        return context