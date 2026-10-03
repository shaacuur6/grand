from django.urls import path
from .views import (
    ExpenseCategoryListView, ExpenseCategoryCreateView, ExpenseCategoryUpdateView,
    ExpenseListView, ExpenseCreateView, ExpenseUpdateView, ExpenseDeleteView,
)

urlpatterns = [
    path('expenses/', ExpenseListView.as_view(), name='expense_list'),
    path('expenses/add/', ExpenseCreateView.as_view(), name='expense_add'),
    path('expenses/<int:pk>/edit/', ExpenseUpdateView.as_view(), name='expense_edit'),
    path('expenses/<int:pk>/delete/', ExpenseDeleteView.as_view(), name='expense_delete'),
    path('expense-categories/', ExpenseCategoryListView.as_view(), name='expense_category_list'),
    path('expense-categories/add/', ExpenseCategoryCreateView.as_view(), name='expense_category_add'),
    path('expense-categories/<int:pk>/edit/', ExpenseCategoryUpdateView.as_view(), name='expense_category_edit'),
]
