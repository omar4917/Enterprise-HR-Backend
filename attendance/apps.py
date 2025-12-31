from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AttendanceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'attendance'
    verbose_name = _('Attendance')

    def ready(self):
        import attendance.signals  # noqa: F401
        
        # Auto-run startup script only when running the server
        import sys
        if 'runserver' in sys.argv:
            from .startup import ensure_default_users
            ensure_default_users()
