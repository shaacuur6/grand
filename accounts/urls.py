from django.urls import path
from django.contrib.auth.views import LogoutView, LoginView
from .views import CustomLoginView, NoPermissionView



urlpatterns = [
    path("logout/", LogoutView.as_view(next_page="login"), name="logout"),
    #path("login/", LoginView.as_view(template_name="accounts/login.html"), name="login"),
    path("login/", CustomLoginView.as_view(), name="login"),
    path("no-permission/", NoPermissionView.as_view(), name="no_permission"),
]