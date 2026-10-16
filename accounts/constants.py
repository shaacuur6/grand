"""Central role policy for Grand HMS.

Role checks are enforced in views, not only in navigation templates.
"""
ADMIN_ROLES = ["admin"]
MANAGEMENT_ROLES = ["admin", "manager"]
HOTEL_ROLES = ["admin", "manager", "reception"]
BILLING_ROLES = ["admin", "manager", "reception"]
# Reception staff do not create restaurant orders; waiter and management do.
RESTAURANT_ROLES = ["admin", "manager", "waiter"]
# Menu can be viewed by kitchen staff; editing menu is management-only.
FOOD_MENU_ROLES = ["admin", "manager", "waiter"]
KITCHEN_ROLES = ["admin", "manager", "kitchen"]
REPORT_ROLES = ["admin", "manager"]
ALL_ROLES = ["admin", "manager", "reception", "waiter", "kitchen"]
