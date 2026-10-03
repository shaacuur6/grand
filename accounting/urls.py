from django.urls import path
from .views import *
urlpatterns=[
path('',AccountingDashboardView.as_view(),name='accounting_dashboard'),path('sync/',SyncView.as_view(),name='accounting_sync'),
path('accounts/',AccountListView.as_view(),name='account_list'),path('accounts/add/',AccountCreateView.as_view(),name='account_add'),path('accounts/<int:pk>/edit/',AccountUpdateView.as_view(),name='account_edit'),
path('periods/',PeriodListView.as_view(),name='period_list'),path('periods/add/',PeriodCreateView.as_view(),name='period_add'),path('periods/<int:pk>/edit/',PeriodUpdateView.as_view(),name='period_edit'),
path('journal/',JournalListView.as_view(),name='journal_list'),path('journal/add/',JournalCreateView.as_view(),name='journal_add'),path('journal/<int:pk>/',JournalDetailView.as_view(),name='journal_detail'),
path('opening-balance/',OpeningBalanceView.as_view(),name='opening_balance'),path('supplier-payables/',SupplierPayablesView.as_view(),name='supplier_payables'),path('inventory-valuation/',InventoryValuationView.as_view(),name='inventory_valuation'),path('supplier-payments/',SupplierPaymentListView.as_view(),name='supplier_payment_list'),path('supplier-payments/add/',SupplierPaymentCreateView.as_view(),name='supplier_payment_add'),
path('inventory-movements/',InventoryMovementListView.as_view(),name='inventory_movement_list'),path('inventory-movements/add/',InventoryMovementCreateView.as_view(),name='inventory_movement_add'),
path('reports/trial-balance/',TrialBalanceView.as_view(),name='trial_balance'),path('reports/profit-loss/',ProfitLossView.as_view(),name='profit_loss'),path('reports/balance-sheet/',BalanceSheetView.as_view(),name='balance_sheet'),path('reports/cash-flow/',CashFlowView.as_view(),name='cash_flow'),
]
