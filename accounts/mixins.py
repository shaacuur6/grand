from django.shortcuts import redirect

class RoleRequiredMixin:
    allowed_roles = []

    def dispatch(self, request, *args, **kwargs):

        if not request.user.is_authenticated:
            return redirect("login")

        if not hasattr(request.user, "userprofile"):
            return redirect("no_permission")

        if request.user.userprofile.role not in self.allowed_roles:
            return redirect("no_permission")

        return super().dispatch(request, *args, **kwargs)