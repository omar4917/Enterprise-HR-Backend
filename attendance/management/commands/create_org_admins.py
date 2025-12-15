"""
Management command to create company-specific admin accounts.
Run with: python manage.py create_org_admins
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from attendance.models import Organization, OrganizationUser


class Command(BaseCommand):
    help = 'Create admin accounts for each organization'

    def handle(self, *args, **options):
        # Define org admins to create
        org_admins = [
            {
                'organization_slug': 'tech-solutions',
                'username': 'tech_admin',
                'email': 'admin@techsolutions.com',
                'password': 'tech123',
                'role': 'org_admin',
            },
            {
                'organization_slug': 'global-trading',
                'username': 'global_admin',
                'email': 'admin@globaltrading.bd',
                'password': 'global123',
                'role': 'org_admin',
            },
            {
                'organization_slug': 'sunrise-garments',
                'username': 'sunrise_admin',
                'email': 'admin@sunrisegarments.com',
                'password': 'sunrise123',
                'role': 'org_admin',
            },
            {
                'organization_slug': 'digital-media',
                'username': 'dma_admin',
                'email': 'admin@digitalmedia.agency',
                'password': 'dma123',
                'role': 'org_admin',
            },
            {
                'organization_slug': 'healthcare-plus',
                'username': 'healthcare_admin',
                'email': 'admin@healthcareplus.com.bd',
                'password': 'health123',
                'role': 'org_admin',
            },
        ]

        created_users = 0
        created_org_users = 0

        self.stdout.write('\nCreating organization admin accounts...\n')

        for admin_data in org_admins:
            try:
                org = Organization.objects.get(slug=admin_data['organization_slug'])
            except Organization.DoesNotExist:
                self.stdout.write(f"  [!] Organization not found: {admin_data['organization_slug']}")
                continue

            # Create or get Django user
            user, user_created = User.objects.get_or_create(
                username=admin_data['username'],
                defaults={
                    'email': admin_data['email'],
                    'is_staff': True,  # Required for Django admin access
                    'is_active': True,
                }
            )

            if user_created:
                user.set_password(admin_data['password'])
                user.save()
                created_users += 1
                self.stdout.write(f"  [+] Created user: {user.username}")
            else:
                self.stdout.write(f"  [*] User already exists: {user.username}")

            # Create OrganizationUser link
            org_user, org_user_created = OrganizationUser.objects.get_or_create(
                user=user,
                defaults={
                    'organization': org,
                    'role': admin_data['role'],
                }
            )

            if org_user_created:
                created_org_users += 1
                self.stdout.write(f"      -> Linked to: {org.name} as {admin_data['role']}")
            else:
                self.stdout.write(f"      -> Already linked to organization")

        # Print summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS('Organization Admin Accounts Created!'))
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(f'\n  Created {created_users} new users')
        self.stdout.write(f'  Created {created_org_users} organization links\n')
        
        self.stdout.write('Login Credentials:')
        self.stdout.write('-' * 50)
        for admin_data in org_admins:
            org_name = admin_data['organization_slug'].replace('-', ' ').title()
            self.stdout.write(f"  {org_name}:")
            self.stdout.write(f"    Username: {admin_data['username']}")
            self.stdout.write(f"    Password: {admin_data['password']}")
            self.stdout.write('')
