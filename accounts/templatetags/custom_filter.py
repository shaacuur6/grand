from django import template

register = template.Library()

@register.filter
def has_role(user, role):
    return hasattr(user, "userprofile") and user.userprofile.role == role


@register.filter
def has_any_role(user, roles):
    return hasattr(user, "userprofile") and user.userprofile.role in roles.split(",")