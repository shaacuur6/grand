from django.shortcuts import redirect
from .models import UserProfile


class RoleRequiredMixin:
    """Require an authenticated user with one of ``allowed_roles``.

    Authorization is enforced on the server, so direct URL access is checked
    even when a navigation link is hidden.
    """
    allowed_roles = ()

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")

        try:
            role = request.user.userprofile.role
        except UserProfile.DoesNotExist:
            role = None

        if role not in self.allowed_roles:
            return redirect("no_permission")

        return super().dispatch(request, *args, **kwargs)
