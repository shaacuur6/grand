from django.urls import path

from .views import BookingPaymentSummaryView, PaymentReceiptView, RevenueView, InvoiceDetailView, Invoice_ListView, PaymentView, PaymentUpdateView, payment_receipt_pdf
from .report_views import (
DailyPaymentReportView,OutstandingBalancesReportView,
FullyPaidInvoicesReportView, PartialPaymentsReportView,
 PaymentMethodReportView,InvoiceSummaryReportView,
 RestaurantPaidPendingReportView,
    ServicePaidPendingReportView,
    RoomPaidPendingReportView,)
urlpatterns = [

     #REPORTS
    path(
    "reports/restaurant-paid-pending/",
    RestaurantPaidPendingReportView.as_view(),
    name="restaurant_paid_pending"
),

path(
    "reports/service-paid-pending/",
    ServicePaidPendingReportView.as_view(),
    name="service_paid_pending"
),

path(
    "reports/room-paid-pending/",
    RoomPaidPendingReportView.as_view(),
    name="room_paid_pending"
),

    #----------------------------------------
    #REPORTS

    path("reports/outstanding/",OutstandingBalancesReportView.as_view(),name="outstanding_balances"),

    path("reports/fully-paid/",FullyPaidInvoicesReportView.as_view(),name="fully_paid_invoices"),

    path("reports/partial-payments/",PartialPaymentsReportView.as_view(),name="partial_payments"),

    path("reports/payment-methods/",PaymentMethodReportView.as_view(),name="payment_method_report"),

    path("reports/invoice-summary/",InvoiceSummaryReportView.as_view(),name="invoice_summary_report"),
    # ----------------------------------------------------------------------

    path('reports/daily-payments/', DailyPaymentReportView.as_view(), name='daily_payment_report'),
    #Checkin/Checkout
    path("receipt/pdf/<int:pk>/", payment_receipt_pdf, name="payment_receipt_pdf"),
    path("receipt/<int:pk>/", PaymentReceiptView.as_view(), name="payment_receipt"),
    path('revenue/',RevenueView.as_view(),name='revenue_report'),
    path('invoices/', Invoice_ListView.as_view(), name='invoice_list'),
    path("invoice/<int:pk>/", InvoiceDetailView.as_view(), name="invoice_detail"),
    path('payment/<int:pk>/', PaymentView.as_view(), name='payment'),
    path("payment/<int:pk>/update/", PaymentUpdateView.as_view(), name="payment_update"),
    path("payment-summary/", BookingPaymentSummaryView.as_view(), name="payment_summary"),
    #path('checkin/<int:pk>/',CheckInView.as_view(),name='check_in'),
    #path('checkout/<int:pk>/',CheckOutView.as_view(),name='check_out'),

    
]