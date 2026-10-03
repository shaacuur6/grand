"""Automatic accounting posting signals.

Operational transactions are posted to the double-entry ledger as soon as they
are saved. The existing rebuild/sync command remains available as a repair and
reconciliation tool, not as part of normal day-to-day operation.
"""
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .services import (
    post_expense,
    post_invoice,
    post_inventory_movement,
    post_payment,
    post_purchase,
    post_supplier_payment,
)
from .models import InventoryMovement, SupplierPayment


@receiver(post_save, sender="billing.Invoice")
def accounting_invoice_saved(sender, instance, **kwargs):
    post_invoice(instance, user=instance.created_by)


@receiver(post_delete, sender="billing.Invoice")
def accounting_invoice_deleted(sender, instance, **kwargs):
    from .models import JournalEntry
    # Invoice revenue is split into room-night/order/service entries.
    JournalEntry.objects.filter(
        source_type__in=["invoice", "invoice_discount"],
        source_id=instance.pk,
    ).delete()
    JournalEntry.objects.filter(
        source_type__in=["invoice_room", "invoice_restaurant", "invoice_service"],
        reference__startswith=f"INV-{instance.pk}/",
    ).delete()
    JournalEntry.objects.filter(
        source_type="invoice_room_night",
        reference__startswith=f"INV-{instance.pk}/",
    ).delete()


@receiver(post_save, sender="billing.Payment")
def accounting_payment_saved(sender, instance, **kwargs):
    post_payment(instance, user=instance.received_by)


@receiver(post_delete, sender="billing.Payment")
def accounting_payment_deleted(sender, instance, **kwargs):
    from .models import JournalEntry
    JournalEntry.objects.filter(source_type="payment", source_id=instance.pk).delete()


@receiver(post_save, sender="finance.Expense")
def accounting_expense_saved(sender, instance, **kwargs):
    post_expense(instance, user=instance.created_by)


@receiver(post_delete, sender="finance.Expense")
def accounting_expense_deleted(sender, instance, **kwargs):
    from .models import JournalEntry
    JournalEntry.objects.filter(source_type="expense", source_id=instance.pk).delete()


@receiver(post_save, sender="purchases.Purchase")
def accounting_purchase_saved(sender, instance, **kwargs):
    post_purchase(instance, user=instance.added_by)


@receiver(post_delete, sender="purchases.Purchase")
def accounting_purchase_deleted(sender, instance, **kwargs):
    from .models import JournalEntry
    JournalEntry.objects.filter(source_type="purchase", source_id=instance.pk).delete()


@receiver(post_save, sender=SupplierPayment)
def accounting_supplier_payment_saved(sender, instance, **kwargs):
    post_supplier_payment(instance, user=instance.created_by)


@receiver(post_delete, sender=SupplierPayment)
def accounting_supplier_payment_deleted(sender, instance, **kwargs):
    from .models import JournalEntry
    JournalEntry.objects.filter(source_type="supplier_payment", source_id=instance.pk).delete()


@receiver(post_save, sender=InventoryMovement)
def accounting_inventory_movement_saved(sender, instance, **kwargs):
    post_inventory_movement(instance, user=instance.created_by)


@receiver(post_delete, sender=InventoryMovement)
def accounting_inventory_movement_deleted(sender, instance, **kwargs):
    from .models import JournalEntry
    JournalEntry.objects.filter(source_type="inventory_movement", source_id=instance.pk).delete()


@receiver(post_save, sender="hotel.RoomStay")
def accounting_room_stay_saved(sender, instance, **kwargs):
    """Room-night revenue changes immediately when a stay is created/edited."""
    from billing.services import sync_invoice
    try:
        sync_invoice(instance.booking)
    except instance.booking.__class__.DoesNotExist:
        pass


@receiver(post_delete, sender="hotel.RoomStay")
def accounting_room_stay_deleted(sender, instance, **kwargs):
    """Recalculate the invoice after a room stay is removed."""
    from billing.services import sync_invoice
    try:
        sync_invoice(instance.booking)
    except instance.booking.__class__.DoesNotExist:
        pass
