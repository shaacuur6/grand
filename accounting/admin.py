from django.contrib import admin
from .models import Account, AccountingPeriod, JournalEntry, JournalLine, SupplierPayment, InventoryMovement
admin.site.register(Account)
admin.site.register(AccountingPeriod)
class JournalLineInline(admin.TabularInline): model=JournalLine; extra=0
@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin): list_display=('date','description','reference','source_type','is_posted'); inlines=[JournalLineInline]
admin.site.register(SupplierPayment)
admin.site.register(InventoryMovement)
