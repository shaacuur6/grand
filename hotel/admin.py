from django.contrib import admin
from .models import Guest, Room, Booking, RoomStay, Booking_History

admin.site.register(Guest)
admin.site.register(Room)
admin.site.register(Booking)
admin.site.register(RoomStay)
admin.site.register(Booking_History)
