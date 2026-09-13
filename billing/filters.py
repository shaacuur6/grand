import django_filters

from .forms import InvoiceFilterForm
from .models import Invoice


class InvoiceFilter(django_filters.FilterSet):
    check_in_from = django_filters.DateFilter(field_name="booking__check_in", lookup_expr="gte")
    check_in_to = django_filters.DateFilter(field_name="booking__check_in", lookup_expr="lte")
    check_out_from = django_filters.DateFilter(field_name="booking__check_out", lookup_expr="gte")
    check_out_to = django_filters.DateFilter(field_name="booking__check_out", lookup_expr="lte")
    guest_name = django_filters.CharFilter(method="filter_guest")
    status = django_filters.ChoiceFilter(
        field_name="booking__status",
        choices=[("reserved", "Reserved"), ("checked_in", "Active"), ("checked_out", "Completed")],
    )

    class Meta:
        model = Invoice
        fields = []
        form = InvoiceFilterForm

    def filter_guest(self, queryset, name, value):
        return queryset.filter(
            booking__guest__first_name__icontains=value
        ) | queryset.filter(
            booking__guest__last_name__icontains=value
        ) | queryset.filter(
            booking__guest__phone__icontains=value
        )
