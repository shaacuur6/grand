"""Backward-compatible imports. Reporting is now centralized in the reports app."""
from reports.views import (
    DailyPaymentReportView, OutstandingBalancesReportView, FullyPaidInvoicesReportView,
    PartialPaymentsReportView, PaymentMethodReportView, InvoiceSummaryReportView,
    RestaurantPaidPendingReportView, ServicePaidPendingReportView, RoomPaidPendingReportView,
)
