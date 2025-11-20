from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Employee
from .utils.sync_helpers import trigger_database_sync_async


@receiver(post_save, sender=Employee)
def employee_saved(sender, instance, **kwargs):
    if kwargs.get("raw"):
        return
    trigger_database_sync_async()


@receiver(post_delete, sender=Employee)
def employee_deleted(sender, instance, **kwargs):
    trigger_database_sync_async()
