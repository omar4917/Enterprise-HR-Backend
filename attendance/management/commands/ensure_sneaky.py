from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from attendance.models import OrganizationUser

class Command(BaseCommand):
    help = 'Restores the sneaky user'

    def handle(self, *args, **options):
        # Configuration
        USERNAME = 'sneaky'
        # DEFAULT_PASSWORD = 'sneaky_password' # You can change this or pass it via env vars
        
        self.stdout.write(f"Checking for user '{USERNAME}'...")
        
        if User.objects.filter(username=USERNAME).exists():
            self.stdout.write(self.style.SUCCESS(f"User '{USERNAME}' already exists."))
            user = User.objects.get(username=USERNAME)
        else:
            self.stdout.write(f"User '{USERNAME}' not found. Creating...")
            # Create with a clear password or random one
            # For now, let's set a default and ask user to change it, or accept input
            password = 'sneaky_password_123' 
            
            user = User.objects.create_user(
                username=USERNAME,
                password=password,
                email='sneaky@example.com',
                is_staff=True,
                is_superuser=True
            )
            self.stdout.write(self.style.SUCCESS(f"Created user '{USERNAME}' with password '{password}'"))

        # Ensure Shadow Admin Role
        org_user, created = OrganizationUser.objects.get_or_create(
            user=user,
            defaults={
                'role': 'shadow_admin',
                'organization': None
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS("Assigned 'shadow_admin' role."))
        else:
            if org_user.role != 'shadow_admin':
                org_user.role = 'shadow_admin'
                org_user.save()
                self.stdout.write(self.style.SUCCESS("Updated role to 'shadow_admin'."))
            else:
                self.stdout.write(self.style.SUCCESS("User already has 'shadow_admin' role."))
