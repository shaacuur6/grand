from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from accounts.constants import MANAGEMENT_ROLES
from accounts.mixins import RoleRequiredMixin
from .forms import ExpenseCategoryForm, ExpenseForm
from .models import Expense, ExpenseCategory

class FinanceRoleMixin(LoginRequiredMixin, RoleRequiredMixin):
    allowed_roles = MANAGEMENT_ROLES

class ExpenseCategoryListView(FinanceRoleMixin, ListView):
    model = ExpenseCategory
    template_name = 'finance/category_list.html'
    context_object_name = 'categories'

class ExpenseCategoryCreateView(FinanceRoleMixin, CreateView):
    model = ExpenseCategory
    form_class = ExpenseCategoryForm
    template_name = 'finance/category_form.html'
    success_url = reverse_lazy('expense_category_list')

class ExpenseCategoryUpdateView(FinanceRoleMixin, UpdateView):
    model = ExpenseCategory
    form_class = ExpenseCategoryForm
    template_name = 'finance/category_form.html'
    success_url = reverse_lazy('expense_category_list')

class ExpenseListView(FinanceRoleMixin, ListView):
    model = Expense
    template_name = 'finance/expense_list.html'
    context_object_name = 'expenses'
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related('category', 'created_by')
        q = self.request.GET.get('q', '').strip()
        category = self.request.GET.get('category')
        if q:
            qs = qs.filter(description__icontains=q) | qs.filter(reference__icontains=q)
        if category:
            qs = qs.filter(category_id=category)
        return qs.order_by('-date', '-id')

    def get_context_data(self, **kwargs):
        c = super().get_context_data(**kwargs)
        c['categories'] = ExpenseCategory.objects.filter(active=True)
        c['total'] = self.get_queryset().aggregate(total=Sum('amount'))['total'] or 0
        return c

class ExpenseCreateView(FinanceRoleMixin, CreateView):
    model = Expense
    form_class = ExpenseForm
    template_name = 'finance/expense_form.html'
    success_url = reverse_lazy('expense_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Expense recorded successfully.')
        return super().form_valid(form)

class ExpenseUpdateView(FinanceRoleMixin, UpdateView):
    model = Expense
    form_class = ExpenseForm
    template_name = 'finance/expense_form.html'
    success_url = reverse_lazy('expense_list')

    def form_valid(self, form):
        messages.success(self.request, 'Expense updated successfully.')
        return super().form_valid(form)

class ExpenseDeleteView(FinanceRoleMixin, DeleteView):
    model = Expense
    template_name = 'finance/expense_confirm_delete.html'
    success_url = reverse_lazy('expense_list')

    def form_valid(self, form):
        messages.success(self.request, 'Expense deleted successfully.')
        return super().form_valid(form)
