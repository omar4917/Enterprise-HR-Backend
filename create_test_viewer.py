import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'attendance_project.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth.models import User
from attendance.models import OrganizationUser, Organization

def create_viewer():
    username = 'test_viewer'
    password = 'password123'
    email = 'viewer@example.com'
    org_name = 'Tech Solutions Ltd' # Use an existing org
    
    # Create or get user
    user, created = User.objects.get_or_create(
        username=username,
        defaults={'email': email, 'is_staff': True}
    )
    user.set_password(password)
    user.save()
    
    # Get organization
    try:
        org = Organization.objects.get(name=org_name)
    except Organization.DoesNotExist:
        org = Organization.objects.create(name=org_name, slug='tech-solutions')
    
    # Create OrganizationUser profile
    ou, ou_created = OrganizationUser.objects.update_or_create(
        user=user,
        defaults={
            'organization': org,
            'role': 'org_viewer'
        }
    )
    
    print(f"User '{username}' with role 'org_viewer' for organization '{org.name}' created/updated successfully.")

if __name__ == '__main__':
    create_viewer()
