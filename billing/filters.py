import django_filters
from .models import Invoice
from .forms import InvoiceFilterForm

class InvoiceFilter(django_filters.FilterSet):

    

    check_in_from = django_filters.DateFilter(
        field_name="booking__check_in",
        lookup_expr="gte"
    )

    check_in_to = django_filters.DateFilter(
        field_name="booking__check_in",
        lookup_expr="lte"
    )

    check_out_from = django_filters.DateFilter(
        field_name="booking__check_out",
        lookup_expr="gte"
    )

    check_out_to = django_filters.DateFilter(
        field_name="booking__check_out",
        lookup_expr="lte"
    )

    guest_name = django_filters.CharFilter(
        field_name="booking__guest__first_name",
        lookup_expr="icontains"
    )

    status = django_filters.ChoiceFilter(
        field_name="booking__status",
        choices=[
            ("checked_in", "Active"),
            ("checked_out", "Completed"),
        ]
    )

    class Meta:
        model = Invoice
        fields = []
        form = InvoiceFilterForm
  

    #    form = InvoiceFilterForm   # 🔥 attach custom form

    def filter_queryset(self, queryset):
        qs = super().filter_queryset(queryset)

        data = self.form.cleaned_data

        if data.get("check_in_from"):
            qs = qs.filter(booking__check_in__gte=data["check_in_from"])

        if data.get("check_in_to"):
            qs = qs.filter(booking__check_in__lte=data["check_in_to"])

        if data.get("check_out_from"):
            qs = qs.filter(booking__check_out__gte=data["check_out_from"])

        if data.get("check_out_to"):
            qs = qs.filter(booking__check_out__lte=data["check_out_to"])

        if data.get("guest_name"):
            qs = qs.filter(
                booking__guest__first_name__icontains=data["guest_name"]
            )

        if data.get("status"):
            qs = qs.filter(booking__status=data["status"])

        return qs