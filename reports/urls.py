from django.urls import path
from .views import (

    DailyCheckInsReportView,
    DailyCheckOutsReportView,
    OccupancyReportView,
    ReservationReportView,
    GuestHistoryReportView,
    RoomRevenueReportView,
    AvailableRoomsReportView,
    OccupiedRoomsReportView,
    RoomCleaningReportView,
    MaintenanceReportView,
    RoomTypeRevenueReportView, StayLedgerReportView)

urlpatterns = [

# ======================================
# ROOM REPORTS
# ======================================

path(
    "available-rooms/",
    AvailableRoomsReportView.as_view(),
    name="available_rooms"
),

path(
    "occupied-rooms/",
    OccupiedRoomsReportView.as_view(),
    name="occupied_rooms"
),

path(
    "room-cleaning/",
    RoomCleaningReportView.as_view(),
    name="room_cleaning"
),

path(
    "maintenance-report/",
    MaintenanceReportView.as_view(),
    name="maintenance_report"
),

path(
    "room-type-revenue/",
    RoomTypeRevenueReportView.as_view(),
    name="room_type_revenue"
),
    # ======================================
# HOTEL REPORTS
# ======================================

path(
    "daily-checkins/",
    DailyCheckInsReportView.as_view(),
    name="daily_checkins"
),

path(
    "daily-checkouts/",
    DailyCheckOutsReportView.as_view(),
    name="daily_checkouts"
),

path(
    "occupancy-report/",
    OccupancyReportView.as_view(),
    name="occupancy_report"
),

path(
    "reservation-report/",
    ReservationReportView.as_view(),
    name="reservation_report"
),

path(
    "guest-history/",
    GuestHistoryReportView.as_view(),
    name="guest_history"
),

path(
    "room-revenue/",
    RoomRevenueReportView.as_view(),
    name="room_revenue"
),
path(
    "stay-ledger/",
    StayLedgerReportView.as_view(),
    name="stay_ledger"
)
]