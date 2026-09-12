from django.contrib.auth.views import LoginView
from django.views.generic import TemplateView

#from rest_framework.decorators import api_view
#from rest_framework.response import Response
from django.contrib.auth import login




class CustomLoginView(LoginView):
    template_name = "accounts/login.html"

    def get_success_url(self):
        role = self.request.user.userprofile.role

        if role == "admin":
            #return "/billing/invoices/"
            self.request.session.set_expiry(900)  # 15 minutes
            return "/grand/hotel/bookings/"
        elif role == "manager":
            self.request.session.set_expiry(1800)  # 15 minutes
            return "/grand/billing/invoices/"
        elif role == "reception":
            self.request.session.set_expiry(3600)  # 15 minutes
            return "/grand/hotel/bookings/"
        elif role == "waiter":
            self.request.session.set_expiry(14400)  # 15 minutes
            return "/grand/restaurant/pos/"
        elif role == "kitchen":
            self.request.session.set_expiry(14400)  # 15 minutes
            return "/grand/restaurant/kitchen/"

        return "/grand/hotel/bookings/"  # Default redirect if role is not recognized


class NoPermissionView(TemplateView):
    template_name = "accounts/no_permission.html"







