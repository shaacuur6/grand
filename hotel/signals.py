from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Booking, Service
from billing.models import Invoice
from billing.services import sync_invoice


@receiver(post_save, sender=Service)
def update_invoice_after_service(sender, instance, **kwargs):
    if instance.booking_id:
        sync_invoice(instance.booking)


@receiver(post_delete, sender=Service)
def update_invoice_after_service_delete(sender, instance, **kwargs):
    if instance.booking_id:
        sync_invoice(instance.booking)
