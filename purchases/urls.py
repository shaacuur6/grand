from django.urls import path

from .views import (
    SupplierListView,
    SupplierCreateView,
    SupplierUpdateView,
    SupplierDeleteView,
    SupplierDetailView,
    InventoryItemListView,
    InventoryItemCreateView,
    InventoryItemUpdateView,
    InventoryItemDeleteView,

    PurchaseListView,
    PurchaseCreateView,
    PurchaseDetailView,
    PurchaseUpdateView,
    PurchaseDeleteView,
)


urlpatterns = [

    # =====================================================
    # SUPPLIERS
    # =====================================================

    path(
        "suppliers/",
        SupplierListView.as_view(),
        name="supplier_list"
    ),

    path(
        "suppliers/add/",
        SupplierCreateView.as_view(),
        name="supplier_create"
    ),

    path(
        "suppliers/<int:pk>/edit/",
        SupplierUpdateView.as_view(),
        name="supplier_update"
    ),

    path(
        "suppliers/<int:pk>/delete/",
        SupplierDeleteView.as_view(),
        name="supplier_delete"
    ),
    path(
        "suppliers/<int:pk>/",
        SupplierDetailView.as_view(),
        name="supplier_detail"
    ),


    # =====================================================
    # INVENTORY
    # =====================================================

    path(
        "inventory/",
        InventoryItemListView.as_view(),
        name="inventoryitem_list"
    ),

    path(
        "inventory/add/",
        InventoryItemCreateView.as_view(),
        name="inventoryitem_create"
    ),

    path(
        "inventory/<int:pk>/edit/",
        InventoryItemUpdateView.as_view(),
        name="inventoryitem_update"
    ),

    path(
        "inventory/<int:pk>/delete/",
        InventoryItemDeleteView.as_view(),
        name="inventoryitem_delete"
    ),


    # =====================================================
    # PURCHASES
    # =====================================================

    path(
        "purchases/",
        PurchaseListView.as_view(),
        name="purchase_list"
    ),

    path(
        "purchases/add/",
        PurchaseCreateView.as_view(),
        name="purchase_add"
    ),

    path(
        "purchases/<int:pk>/",
        PurchaseDetailView.as_view(),
        name="purchase_detail"
    ),

    path(
        "purchases/<int:pk>/edit/",
        PurchaseUpdateView.as_view(),
        name="purchase_update"
    ),

    path(
        "purchases/<int:pk>/delete/",
        PurchaseDeleteView.as_view(),
        name="purchase_delete"
    ),

]