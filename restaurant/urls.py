from django.urls import path

from .views import (
    POSView, ReceiptView, OrderListView, OrderDetailView, OrderUpdateView, OrderDeleteView, OrderItemReportView,
    FoodListView, FoodCreateView, FoodUpdateView, FoodDeleteView,
    FoodCategoryListView, FoodCategoryCreateView, FoodCategoryUpdateView, FoodCategoryDeleteView,
    EmployeeListView, EmployeeCreateView, EmployeeUpdateView, EmployeeDeleteView,
)

urlpatterns = [
    path("pos/", POSView.as_view(), name="pos"),
    path("receipt/<int:pk>/", ReceiptView.as_view(), name="print_receipt"),
    path("orders/", OrderListView.as_view(), name="orders_report"),
    path("orders/<int:pk>/", OrderDetailView.as_view(), name="order_detail"),
    path("order/<int:pk>/update/", OrderUpdateView.as_view(), name="order_update"),
    path("order/<int:pk>/delete/", OrderDeleteView.as_view(), name="order_delete"),
    path("order-items/", OrderItemReportView.as_view(), name="order_item_report"),
    path("menu/", FoodListView.as_view(), name="food_list"),
    path("menu/add/", FoodCreateView.as_view(), name="menu_add"),
    path("menu/<int:pk>/edit/", FoodUpdateView.as_view(), name="menu_edit"),
    path("menu/<int:pk>/delete/", FoodDeleteView.as_view(), name="menu_delete"),
    path("categories/", FoodCategoryListView.as_view(), name="category_list"),
    path("categories/add/", FoodCategoryCreateView.as_view(), name="category_add"),
    path("categories/<int:pk>/edit/", FoodCategoryUpdateView.as_view(), name="category_edit"),
    path("categories/<int:pk>/delete/", FoodCategoryDeleteView.as_view(), name="category_delete"),
    path("employees/", EmployeeListView.as_view(), name="employee_list"),
    path("employees/add/", EmployeeCreateView.as_view(), name="employee_add"),
    path("employees/<int:pk>/edit/", EmployeeUpdateView.as_view(), name="employee_edit"),
    path("employees/<int:pk>/delete/", EmployeeDeleteView.as_view(), name="employee_delete"),
]
