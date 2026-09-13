from django.urls import path

from .views import (
    InvoiceListView, InvoiceDetailView, InvoiceUpdateView,
    PaymentSummaryView, PaymentView, PaymentListView, PaymentUpdateView,
    PaymentDeleteView, PaymentReceiptView, payment_receipt_pdf, RevenueView,
)

urlpatterns = [
    path("invoices/", InvoiceListView.as_view(), name="invoice_list"),
    path("invoice/<int:pk>/", InvoiceDetailView.as_view(), name="invoice_detail"),
    path("invoice/<int:pk>/discount/", InvoiceUpdateView.as_view(), name="invoice_discount"),
    path("payment-summary/", PaymentSummaryView.as_view(), name="payment_summary"),
    path("payments/", PaymentListView.as_view(), name="payment_list"),
    path("payment/<int:pk>/", PaymentView.as_view(), name="payment"),
    path("payment/<int:pk>/update/", PaymentUpdateView.as_view(), name="payment_update"),
    path("payment/<int:pk>/delete/", PaymentDeleteView.as_view(), name="payment_delete"),
    path("receipt/<int:pk>/", PaymentReceiptView.as_view(), name="payment_receipt"),
    path("receipt/pdf/<int:pk>/", payment_receipt_pdf, name="payment_receipt_pdf"),
    path("revenue/", RevenueView.as_view(), name="revenue_report"),
]
