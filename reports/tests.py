from datetime import date, datetime, time
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from accounting.models import SupplierPayment
from billing.models import Invoice, Payment
from finance.models import Expense, ExpenseCategory
from hotel.models import Booking, Guest, Room, RoomStay
from purchases.models import Supplier
from restaurant.models import FoodCategory, FoodItem, Order, OrderItem
from reports.forms import DateRangeForm, ReportFilterForm
from reports.views import (
    cash_flow_summary,
    category_sales_rows,
    invoice_paid_as_of,
    filter_booking_dates,
    stay_rows,
    top_selling_food_rows,
)


class ReportRegressionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="report-test", password="unused")
        cls.category_a = FoodCategory.objects.create(name="Hot Drinks", created_by=cls.user)
        cls.category_b = FoodCategory.objects.create(name="Desserts", created_by=cls.user)
        cls.food_a = FoodItem.objects.create(name="Tea", category=cls.category_a, price=Decimal("2.50"))
        cls.food_b = FoodItem.objects.create(name="Cake", category=cls.category_b, price=Decimal("5.00"))
        cls.order = Order.objects.create(waiter=cls.user, total_amount=Decimal("7.50"))
        OrderItem.objects.create(order=cls.order, food=cls.food_a, quantity=1)
        OrderItem.objects.create(order=cls.order, food=cls.food_b, quantity=1)
        cls.order_two = Order.objects.create(waiter=cls.user, total_amount=Decimal("5.00"))
        OrderItem.objects.create(order=cls.order_two, food=cls.food_a, quantity=2)

    def test_top_food_filter_only_aggregates_selected_food_items(self):
        form = DateRangeForm({"food": str(self.food_a.pk)})
        rows = list(top_selling_food_rows(Order.objects.all(), form))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["food_id"], self.food_a.pk)
        self.assertEqual(rows[0]["total_qty"], 3)
        self.assertEqual(rows[0]["sales"], Decimal("7.50"))

    def test_category_filter_only_aggregates_items_in_selected_category(self):
        form = DateRangeForm({"category": str(self.category_a.pk)})
        rows = list(category_sales_rows(Order.objects.all(), form))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["food__category_id"], self.category_a.pk)
        self.assertEqual(rows[0]["total_qty"], 3)
        self.assertEqual(rows[0]["total_sales"], Decimal("7.50"))

    def _booking_with_stay(self, start, end, status="checked_out"):
        guest = Guest.objects.create(first_name="Test", last_name="Guest", phone="123")
        room = Room.objects.create(number=901, room_type="single", price=100, price_with_ac=120)
        booking = Booking.objects.create(
            guest=guest, room=room, check_in=start, check_out=end,
            status=status, room_price=Decimal("100.00"), created_by=self.user,
        )
        stay = RoomStay.objects.create(
            booking=booking, room=room, start_date=start, end_date=end,
            rate=Decimal("100.00"),
        )
        return booking, stay

    def test_room_revenue_respects_inclusive_selected_date_range(self):
        booking, _ = self._booking_with_stay(date(2026, 1, 1), date(2026, 1, 5))
        rows, total = stay_rows(
            Booking.objects.filter(pk=booking.pk),
            start=date(2026, 1, 2), end=date(2026, 1, 3), today=date(2026, 1, 10),
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["nights"], 2)
        self.assertEqual(total, Decimal("200.00"))

    def test_checkout_filter_uses_the_whole_selected_date_range(self):
        guest = Guest.objects.create(first_name="Checkout", last_name="Guest", phone="789")
        room = Room.objects.create(number=903, room_type="single", price=100, price_with_ac=120)
        first = Booking.objects.create(guest=guest, room=room, check_in=date(2026, 1, 1), check_out=date(2026, 1, 2), status="checked_out", room_price=Decimal("100.00"), created_by=self.user)
        # The same room can be reused for historical booking records in this test.
        room2 = Room.objects.create(number=904, room_type="single", price=100, price_with_ac=120)
        second = Booking.objects.create(guest=guest, room=room2, check_in=date(2026, 1, 4), check_out=date(2026, 1, 5), status="checked_out", room_price=Decimal("100.00"), created_by=self.user)
        form = ReportFilterForm({"start_date": "2026-01-02", "end_date": "2026-01-04"})
        results = filter_booking_dates(Booking.objects.all(), form, "check_out", today=date(2026, 1, 10))
        self.assertEqual(list(results.values_list("pk", flat=True)), [first.pk])

    def test_invoice_paid_total_is_capped_at_report_end_date(self):
        guest = Guest.objects.create(first_name="Invoice", last_name="Guest", phone="456")
        room = Room.objects.create(number=902, room_type="single", price=100, price_with_ac=120)
        booking = Booking.objects.create(
            guest=guest, room=room, check_in=date(2026, 1, 1), check_out=date(2026, 1, 2),
            status="checked_out", room_price=Decimal("100.00"), created_by=self.user,
        )
        invoice = Invoice.objects.create(booking=booking, room_total=Decimal("100.00"), total=Decimal("100.00"))
        payment_before = Payment.objects.create(invoice=invoice, amount=Decimal("30.00"), payment_method="cash")
        payment_after = Payment.objects.create(invoice=invoice, amount=Decimal("40.00"), payment_method="cash")
        Payment.objects.filter(pk=payment_before.pk).update(created=timezone.make_aware(datetime.combine(date(2026, 1, 2), time(10, 0))))
        Payment.objects.filter(pk=payment_after.pk).update(created=timezone.make_aware(datetime.combine(date(2026, 1, 5), time(10, 0))))
        invoice.refresh_from_db()
        self.assertEqual(invoice_paid_as_of(invoice, date(2026, 1, 3)), Decimal("30.00"))
        self.assertEqual(invoice_paid_as_of(invoice, None), Decimal("70.00"))

def test_cash_flow_uses_recorded_supplier_payments_not_purchase_orders(self):
    supplier = Supplier.objects.create(
        name="Test Supplier",
        created_by=self.user,
    )

    category, _ = ExpenseCategory.objects.get_or_create(
        name="Utilities"
    )

    Expense.objects.create(
        category=category,
        description="Electricity",
        amount=Decimal("15.00"),
        date=date(2026, 1, 3),
        payment_method="bank",
        created_by=self.user,
    )

    SupplierPayment.objects.create(
        supplier=supplier,
        date=date(2026, 1, 4),
        amount=Decimal("25.00"),
        payment_method="cash",
        created_by=self.user,
    )

    summary = cash_flow_summary(
        date(2026, 1, 1),
        date(2026, 1, 31),
    )

    self.assertEqual(summary["supplier_payments"], Decimal("25.00"))
    self.assertEqual(summary["expenses"], Decimal("15.00"))
    self.assertEqual(summary["operating_outflow"], Decimal("40.00"))
    self.assertEqual(
        summary["net_cash"],
        summary["collections"] - Decimal("40.00"),
    )