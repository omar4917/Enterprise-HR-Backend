import threading
from django.db import close_old_connections


def trigger_database_sync_async():
    """
    Fire-and-forget push notification to make devices refresh their local DB.
    """
    def _task():
        from attendance.models import DeviceRegistration
        from attendance.utils.push_helpers import send_database_update_notification

        close_old_connections()
        tokens = DeviceRegistration.objects.values_list("token", flat=True)
        send_database_update_notification(tokens)

    threading.Thread(target=_task, daemon=True).start()
