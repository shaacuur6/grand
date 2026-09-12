from django.utils import timezone
from datetime import datetime

from django.views.generic import TemplateView
from django.db.models import Sum, Count

from django.contrib.auth.models import User

from restaurant.models import (
    Order,
    OrderItem,
    FoodItem,
    FoodCategory
)

from billing.models import (
    RestaurantPaymentAllocation,
    Payment
)


# =========================================
# WAITER SALES REPORT
# =========================================

class WaiterSalesReportView(TemplateView):

    template_name = (
        "reports/restaurant/waiter_sales.html"
    )

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        report = []

        waiters = User.objects.all()

        for waiter in waiters:

            orders = Order.objects.filter(
                waiter=waiter
            )

            total_sales = orders.aggregate(
                total=Sum("total_amount")
            )["total"] or 0

            report.append({

                "waiter": waiter,
                "total_sales": total_sales

            })

        context["report"] = report

        return context


# =========================================
# ORDERS PER WAITER
# =========================================

class OrdersPerWaiterReportView(TemplateView):

    template_name = (
        "reports/restaurant/orders_per_waiter.html"
    )

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        report = []

        waiters = User.objects.all()

        for waiter in waiters:

            total_orders = Order.objects.filter(
                waiter=waiter
            ).count()

            report.append({

                "waiter": waiter,
                "total_orders": total_orders

            })

        context["report"] = report

        return context


# =========================================
# COLLECTIONS PER WAITER
# =========================================

class CollectionsPerWaiterReportView(TemplateView):

    template_name = (
        "reports/restaurant/collections_per_waiter.html"
    )

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        report = []

        waiters = User.objects.all()

        for waiter in waiters:

            total_collected = Payment.objects.filter(
                received_by=waiter
            ).aggregate(
                total=Sum("amount")
            )["total"] or 0

            report.append({

                "waiter": waiter,
                "total_collected": total_collected

            })

        context["report"] = report

        return context


# =========================================
# UNPAID ORDERS PER WAITER
# =========================================

class UnpaidOrdersPerWaiterReportView(TemplateView):

    template_name = (
        "reports/restaurant/unpaid_orders_per_waiter.html"
    )

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        report = []

        waiters = User.objects.all()

        for waiter in waiters:

            orders = Order.objects.filter(
                waiter=waiter
            )

            unpaid_total = 0

            for order in orders:

                paid = (
                    RestaurantPaymentAllocation.objects
                    .filter(order=order)
                    .aggregate(total=Sum("amount"))
                )["total"] or 0

                pending = order.total_amount - paid

                unpaid_total += pending

            report.append({

                "waiter": waiter,
                "unpaid_total": unpaid_total

            })

        context["report"] = report

        return context
    


# =========================================
# DAILY RESTAURANT SALES
# =========================================

class DailyRestaurantSalesReportView(TemplateView):

    template_name = (
        "reports/restaurant/daily_sales.html"
    )

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        today = timezone.now().date()

        orders = Order.objects.filter(
            created_at__date=today
        )

        total_sales = orders.aggregate(
            total=Sum("total_amount")
        )["total"] or 0

        context["orders"] = orders
        context["total_sales"] = total_sales
        context["today"] = today

        return context


# =========================================
# MONTHLY SALES
# =========================================

class MonthlySalesReportView(TemplateView):

    template_name = (
        "reports/restaurant/monthly_sales.html"
    )

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        now = timezone.now()

        orders = Order.objects.filter(
            created_at__year=now.year,
            created_at__month=now.month
        )

        total_sales = orders.aggregate(
            total=Sum("total_amount")
        )["total"] or 0

        context["orders"] = orders
        context["total_sales"] = total_sales
        context["month"] = now.strftime("%B %Y")

        return context


# =========================================
# TOP SELLING FOODS
# =========================================

class TopSellingFoodsReportView(TemplateView):

    template_name = (
        "reports/restaurant/top_selling_foods.html"
    )

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        foods = (

            OrderItem.objects
            .values(

                "food__name"

            )
            .annotate(

                total_qty=Sum("quantity")

            )
            .order_by("-total_qty")

        )

        context["foods"] = foods

        return context


# =========================================
# CATEGORY SALES
# =========================================

class CategorySalesReportView(TemplateView):

    template_name = (
        "reports/restaurant/category_sales.html"
    )

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        categories = []

        for category in FoodCategory.objects.all():

            total = OrderItem.objects.filter(
                food__category=category
            ).aggregate(

                total=Sum("food__price")

            )["total"] or 0

            categories.append({

                "category": category,
                "total": total

            })

        context["categories"] = categories

        return context


# =========================================
# ORDER HISTORY
# =========================================

class OrderHistoryReportView(TemplateView):

    template_name = (
        "reports/restaurant/order_history.html"
    )

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        orders = Order.objects.all().order_by(
            "-created_at"
        )

        context["orders"] = orders

        return context


# =========================================
# TABLE SALES
# =========================================

class TableSalesReportView(TemplateView):

    template_name = (
        "reports/restaurant/table_sales.html"
    )

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        tables = (

            Order.objects
            .values("table_number")
            .annotate(

                total_sales=Sum("total_amount"),
                total_orders=Count("id")

            )
            .order_by("-total_sales")

        )

        context["tables"] = tables

        return context
