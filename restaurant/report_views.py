"""Backward-compatible imports. Reporting is now centralized in the reports app."""
from reports.views import (
    WaiterSalesReportView, OrdersPerWaiterReportView, CollectionsPerWaiterReportView,
    UnpaidOrdersPerWaiterReportView, DailyRestaurantSalesReportView, MonthlySalesReportView,
    TopSellingFoodsReportView, CategorySalesReportView, OrderHistoryReportView, TableSalesReportView,
)
