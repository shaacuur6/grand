from django.urls import path
from .views import(
    FoodListView, FoodCreateView,FoodUpdateView, POSView,FoodCategoryListView,
 FoodCategoryCreateView,FoodCategoryDeleteView,FoodCategoryUpdateView,
 OrderItemReportView,OrderListView,OrderUpdateView, OrderDetailView
 ,ReceiptView
)


from .report_views import (

    WaiterSalesReportView,
    OrdersPerWaiterReportView,
    CollectionsPerWaiterReportView,
    UnpaidOrdersPerWaiterReportView,
    DailyRestaurantSalesReportView,
    MonthlySalesReportView,
    TopSellingFoodsReportView,
    CategorySalesReportView,
    OrderHistoryReportView,
    TableSalesReportView,
)


urlpatterns = [
    # ======================================
# RESTAURANT REPORTS
# ======================================

path(
    "reports/daily-sales/",
    DailyRestaurantSalesReportView.as_view(),
    name="daily_restaurant_sales"
),

path(
    "reports/monthly-sales/",
    MonthlySalesReportView.as_view(),
    name="monthly_sales"
),

path(
    "reports/top-selling-foods/",
    TopSellingFoodsReportView.as_view(),
    name="top_selling_foods"
),

path(
    "reports/category-sales/",
    CategorySalesReportView.as_view(),
    name="category_sales"
),

path(
    "reports/order-history/",
    OrderHistoryReportView.as_view(),
    name="order_history"
),

path(
    "reports/table-sales/",
    TableSalesReportView.as_view(),
    name="table_sales"
),
    # ======================================
# WAITER REPORTS
# ======================================

path(
    "reports/waiter-sales/",
    WaiterSalesReportView.as_view(),
    name="waiter_sales"
),

path(
    "reports/orders-per-waiter/",
    OrdersPerWaiterReportView.as_view(),
    name="orders_per_waiter"
),

path(
    "reports/collections-per-waiter/",
    CollectionsPerWaiterReportView.as_view(),
    name="collections_per_waiter"
),

path(
    "reports/unpaid-orders-per-waiter/",
    UnpaidOrdersPerWaiterReportView.as_view(),
    name="unpaid_orders_per_waiter"
),
   
    path("receipt/<int:pk>/", ReceiptView.as_view(), name="print_receipt"),

    path('menu/', FoodListView.as_view(), name='food_list'),
    path('menu/add/', FoodCreateView.as_view(), name='menu_add'),
    path('menu/<int:pk>/edit/', FoodUpdateView.as_view(), name='menu_edit'),
    path('categories/', FoodCategoryListView.as_view(), name='category_list'),
    path('categories/add/', FoodCategoryCreateView.as_view(), name='category_add'), 
    path('categories/<int:pk>/edit/', FoodCategoryUpdateView.as_view(), name='category_edit'),
    path('categories/<int:pk>/delete/', FoodCategoryDeleteView.as_view(), name='category_delete'),  
    path('pos/',POSView.as_view(),name='pos'),
    path('order-items/',OrderItemReportView.as_view(),name='order_item_report'),
    path('orders/',OrderListView.as_view(),name='orders_report'),
    path("order/<int:pk>/update/", OrderUpdateView.as_view(), name="order_update"),
    
    
    path('orders/<int:pk>/',OrderDetailView.as_view(),name='order_detail'),

]