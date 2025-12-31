from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from attendance.models import OrganizationUser

class Command(BaseCommand):
    help = 'Restores the super admin user admin@example.com'

    def handle(self, *args, **options):
        # Configuration
        USERNAME = 'admin'
        EMAIL = 'admin@example.com'
        PASSWORD = 'admin'  # Simple default password
        
        self.stdout.write(f"Checking for user '{EMAIL}'...")
        
        user = User.objects.filter(email=EMAIL).first()
        if not user:
            user = User.objects.filter(username=USERNAME).first()

        if user:
            self.stdout.write(self.style.SUCCESS(f"User '{user.username}' ({user.email}) already exists."))
            if not user.is_superuser:
                 user.is_superuser = True
                 user.is_staff = True
                 user.save()
                 self.stdout.write(self.style.SUCCESS("Promoted to superuser/staff."))
        else:
            self.stdout.write(f"User '{EMAIL}' not found. Creating...")
            user = User.objects.create_user(
                username=USERNAME,
                password=PASSWORD,
                email=EMAIL,
                is_staff=True,
                is_superuser=True
            )
            self.stdout.write(self.style.SUCCESS(f"Created user '{USERNAME}' ({EMAIL}) with password '{PASSWORD}'"))

        # Ensure Role (optional if is_superuser is handled by checks, but good for multi-tenancy consistency)
        # Check if OrgUser entry exists
        org_user, created = OrganizationUser.objects.get_or_create(
            user=user,
            defaults={
                'role': 'super_admin',
                'organization': None
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS("Assigned 'super_admin' role."))
        else:
            if org_user.role != 'super_admin':
                 org_user.role = 'super_admin'
                 org_user.save()
                 self.stdout.write(self.style.SUCCESS("Updated role to 'super_admin'."))
            else:
                 self.stdout.write(self.style.SUCCESS("User is already 'super_admin'."))
