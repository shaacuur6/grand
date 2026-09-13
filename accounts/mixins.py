from django.shortcuts import redirect


class RoleRequiredMixin:
    """Require an authenticated user with one of ``allowed_roles``."""

    allowed_roles = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")

        profile = getattr(request.user, "userprofile", None)
        if profile is None or profile.role not in self.allowed_roles:
            return redirect("no_permission")

        return super().dispatch(request, *args, **kwargs)
