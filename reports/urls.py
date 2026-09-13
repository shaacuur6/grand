from django.urls import path

from .views import (
    ReportsDashboardView, DailyCheckInsReportView, DailyCheckOutsReportView, ReservationReportView, GuestHistoryReportView,
    RoomRevenueReportView, StayLedgerReportView, OccupancyReportView, AvailableRoomsReportView, OccupiedRoomsReportView,
    RoomCleaningReportView, MaintenanceReportView, RoomTypeRevenueReportView,
    DailyPaymentReportView, PaymentMethodReportView, InvoiceSummaryReportView, OutstandingBalancesReportView,
    FullyPaidInvoicesReportView, PartialPaymentsReportView, RestaurantPaidPendingReportView, ServicePaidPendingReportView, RoomPaidPendingReportView,
    DailyRestaurantSalesReportView, MonthlySalesReportView, WaiterSalesReportView, OrdersPerWaiterReportView, CollectionsPerWaiterReportView,
    UnpaidOrdersPerWaiterReportView, TopSellingFoodsReportView, CategorySalesReportView, OrderHistoryReportView, TableSalesReportView,
    PurchaseReportView, SupplierPurchaseReportView, LowStockReportView, RestaurantSalesExcelView, RestaurantSalesPDFView,
)

urlpatterns = [
    path("", ReportsDashboardView.as_view(), name="reports_dashboard"),
    # Hotel
    path("hotel/daily-checkins/", DailyCheckInsReportView.as_view(), name="daily_checkins"),
    path("hotel/daily-checkouts/", DailyCheckOutsReportView.as_view(), name="daily_checkouts"),
    path("hotel/reservations/", ReservationReportView.as_view(), name="reservation_report"),
    path("hotel/guest-history/", GuestHistoryReportView.as_view(), name="guest_history"),
    path("hotel/room-revenue/", RoomRevenueReportView.as_view(), name="room_revenue"),
    path("hotel/stay-ledger/", StayLedgerReportView.as_view(), name="stay_ledger"),
    path("hotel/occupancy/", OccupancyReportView.as_view(), name="occupancy_report"),
    path("hotel/available-rooms/", AvailableRoomsReportView.as_view(), name="available_rooms"),
    path("hotel/occupied-rooms/", OccupiedRoomsReportView.as_view(), name="occupied_rooms"),
    path("hotel/cleaning/", RoomCleaningReportView.as_view(), name="room_cleaning"),
    path("hotel/maintenance/", MaintenanceReportView.as_view(), name="maintenance_report"),
    path("hotel/room-type-revenue/", RoomTypeRevenueReportView.as_view(), name="room_type_revenue"),
    # Billing
    path("billing/daily-payments/", DailyPaymentReportView.as_view(), name="daily_payment_report"),
    path("billing/payment-methods/", PaymentMethodReportView.as_view(), name="payment_method_report"),
    path("billing/invoice-summary/", InvoiceSummaryReportView.as_view(), name="invoice_summary_report"),
    path("billing/outstanding/", OutstandingBalancesReportView.as_view(), name="outstanding_balances"),
    path("billing/fully-paid/", FullyPaidInvoicesReportView.as_view(), name="fully_paid_invoices"),
    path("billing/partial-payments/", PartialPaymentsReportView.as_view(), name="partial_payments"),
    path("billing/restaurant/", RestaurantPaidPendingReportView.as_view(), name="restaurant_paid_pending"),
    path("billing/services/", ServicePaidPendingReportView.as_view(), name="service_paid_pending"),
    path("billing/rooms/", RoomPaidPendingReportView.as_view(), name="room_paid_pending"),
    # Restaurant
    path("restaurant/daily-sales/", DailyRestaurantSalesReportView.as_view(), name="daily_restaurant_sales"),
    path("restaurant/monthly-sales/", MonthlySalesReportView.as_view(), name="monthly_sales"),
    path("restaurant/waiter-sales/", WaiterSalesReportView.as_view(), name="waiter_sales"),
    path("restaurant/orders-per-waiter/", OrdersPerWaiterReportView.as_view(), name="orders_per_waiter"),
    path("restaurant/collections-per-waiter/", CollectionsPerWaiterReportView.as_view(), name="collections_per_waiter"),
    path("restaurant/unpaid-orders-per-waiter/", UnpaidOrdersPerWaiterReportView.as_view(), name="unpaid_orders_per_waiter"),
    path("restaurant/top-selling-foods/", TopSellingFoodsReportView.as_view(), name="top_selling_foods"),
    path("restaurant/category-sales/", CategorySalesReportView.as_view(), name="category_sales"),
    path("restaurant/order-history/", OrderHistoryReportView.as_view(), name="order_history"),
    path("restaurant/table-sales/", TableSalesReportView.as_view(), name="table_sales"),
    path("restaurant/export/excel/", RestaurantSalesExcelView.as_view(), name="export_excel"),
    path("restaurant/export/pdf/", RestaurantSalesPDFView.as_view(), name="export_pdf"),
    # Purchases
    path("purchases/", PurchaseReportView.as_view(), name="purchase_report"),
    path("purchases/by-supplier/", SupplierPurchaseReportView.as_view(), name="supplier_purchase_report"),
    path("purchases/low-stock/", LowStockReportView.as_view(), name="low_stock_report"),
]
