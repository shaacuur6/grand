from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from billing.services import sync_invoice
from .models import Order, OrderItem


@receiver(post_save, sender=Order)
def update_invoice_after_order(sender, instance, **kwargs):
    if instance.booking_id:
        sync_invoice(instance.booking)


@receiver(post_delete, sender=Order)
def update_invoice_after_order_delete(sender, instance, **kwargs):
    if instance.booking_id:
        sync_invoice(instance.booking)


@receiver(post_save, sender=OrderItem)
def update_order_total_after_item(sender, instance, **kwargs):
    order = instance.order
    order.update_total()


@receiver(post_delete, sender=OrderItem)
def update_order_total_after_item_delete(sender, instance, **kwargs):
    order = instance.order
    order.update_total()
