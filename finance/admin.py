from django.contrib import admin
from .models import Expense, ExpenseCategory

@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'active', 'created')
    search_fields = ('name',)

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('date', 'description', 'category', 'amount', 'payment_method', 'created_by')
    list_filter = ('category', 'payment_method', 'date')
    search_fields = ('description', 'reference', 'notes')
    date_hierarchy = 'date'
