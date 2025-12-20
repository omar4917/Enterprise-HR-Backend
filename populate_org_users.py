"""
Script to populate OrganizationUser records for existing users
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth.models import User
from attendance.models import OrganizationUser, Organization

print("=== Current State ===")
print("OrganizationUsers:")
for ou in OrganizationUser.objects.select_related('user', 'organization').all():
    org_name = ou.organization.name if ou.organization else "None (super_admin)"
    print(f"  {ou.id}: {ou.user.username} -> {org_name} ({ou.role}) main={ou.is_main_admin}")

print("\nUsers without OrganizationUser profile:")
for user in User.objects.all():
    if not hasattr(user, 'org_profile') or not OrganizationUser.objects.filter(user=user).exists():
        print(f"  {user.id}: {user.username}")

# Map usernames to organizations
ORG_MAPPING = {
    'dlwlrma': None,  # Super admin - no org
    'admin': None,    # Super admin - no org
    'tech_admin': 'Tech Solutions Ltd',
    'global_admin': 'Global Trading Co.',
    'sunrise_admin': 'Sunrise Garments',
    'dma_admin': 'Digital Media Agency',
    'healthcare_admin': 'Healthcare Plus Hospital',
}

print("\n=== Creating/Updating OrganizationUser records ===")
for username, org_name in ORG_MAPPING.items():
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        print(f"  User {username} not found, skipping")
        continue
    
    org = None
    if org_name:
        try:
            org = Organization.objects.get(name=org_name)
        except Organization.DoesNotExist:
            print(f"  Org {org_name} not found, skipping {username}")
            continue
    
    role = 'super_admin' if org is None else 'org_main_admin'
    is_main = (role == 'org_main_admin')
    
    ou, created = OrganizationUser.objects.update_or_create(
        user=user,
        defaults={
            'organization': org,
            'role': role,
            'is_main_admin': is_main,
        }
    )
    action = "Created" if created else "Updated"
    org_display = org.name if org else "None (super_admin)"
    print(f"  {action}: {username} -> {org_display} ({role})")

print("\n=== Final State ===")
for ou in OrganizationUser.objects.select_related('user', 'organization').all():
    org_name = ou.organization.name if ou.organization else "All (super_admin)"
    print(f"  {ou.user.username} -> {org_name} ({ou.role}) main={ou.is_main_admin}")
