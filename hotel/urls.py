from django.urls import path
from .views import (
    RoomListView,
    RoomCreateView,
    RoomUpdateView,
    BookingListView, BookingDetailView,
    BookingCreateView,
    BookingUpdateView,
    BookingDeleteView, BookingCheckOutView,
    GuestListView, GuestCreateView, GuestUpdateView,GuestCreateAjaxView,
    CheckInView, DashboardView,ServiceListView, ServiceCreateView,
    ServiceUpdateView, ServiceDeleteView, RoomTransferView

)


urlpatterns = [

    #Services
    path("services/", ServiceListView.as_view(), name="service_list"),
    path("services/add/", ServiceCreateView.as_view(), name="service_add"),
    path("services/<int:pk>/edit/", ServiceUpdateView.as_view(), name="service_edit"),
    path("services/<int:pk>/delete/", ServiceDeleteView.as_view(), name="service_delete"),
    path( "",DashboardView.as_view(),name="dashboard"),
    # Guests
    path('guests/', GuestListView.as_view(), name='guest_list'),

    path('guests/add/', GuestCreateView.as_view(), name='guest_add'),

    path("guest/ajax/add/", GuestCreateAjaxView.as_view(), name="guest_add_ajax"),

    path('guests/<int:pk>/edit/', GuestUpdateView.as_view(), name='guest_edit'),
    
    #Checkin/Checkout

    path('checkin/<int:pk>/',CheckInView.as_view(),name='check_in'),
    path('checkout/<int:pk>/',BookingCheckOutView.as_view(),name='check_out'),
    path('booking/<int:pk>/check_out/', BookingCheckOutView.as_view(), name='booking_check_out'),
    # rooms
    path('rooms/', RoomListView.as_view(), name='room_list'),
    path('rooms/add/', RoomCreateView.as_view(), name='room_add'),
    path('rooms/<int:pk>/edit/', RoomUpdateView.as_view(), name='room_edit'),

    # bookings
    path('bookings/', BookingListView.as_view(), name='booking_list'),
    path('bookings/add/', BookingCreateView.as_view(), name='booking_add'),
    path("booking/<int:pk>/", BookingDetailView.as_view(), name="booking_detail"),
    path("booking/<int:pk>/update/", BookingUpdateView.as_view(), name="booking_update"),
    path("booking/<int:pk>/transfer/", RoomTransferView.as_view(), name="room_transfer"),
    path("booking/<int:pk>/delete/", BookingDeleteView.as_view(), name="booking_delete"),
]