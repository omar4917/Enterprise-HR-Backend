"""
Data migration to create default organization and assign existing records.

This migration:
1. Creates a default organization for existing data
2. Assigns all existing Employees to the default organization
3. Assigns all existing AttendanceRecords to the default organization
4. Assigns all existing LiveFeedImages to the default organization
5. Creates a default device for the default organization
"""

from django.db import migrations


def create_default_organization(apps, schema_editor):
    """Create default organization and assign all existing records to it."""
    Organization = apps.get_model('attendance', 'Organization')
    OrganizationSettings = apps.get_model('attendance', 'OrganizationSettings')
    Device = apps.get_model('attendance', 'Device')
    Employee = apps.get_model('attendance', 'Employee')
    AttendanceRecord = apps.get_model('attendance', 'AttendanceRecord')
    LiveFeedImage = apps.get_model('attendance', 'LiveFeedImage')
    
    # Check if there are any existing records that need migration
    employees_without_org = Employee.objects.filter(organization__isnull=True).count()
    records_without_org = AttendanceRecord.objects.filter(organization__isnull=True).count()
    images_without_org = LiveFeedImage.objects.filter(organization__isnull=True).count()
    
    if employees_without_org == 0 and records_without_org == 0 and images_without_org == 0:
        # No migration needed
        return
    
    # Create default organization
    default_org, created = Organization.objects.get_or_create(
        slug='default',
        defaults={
            'name': 'Default Organization',
            'is_active': True,
            'max_employees': 1000,
            'max_devices': 10,
        }
    )
    
    if created:
        # Create settings for the new organization
        OrganizationSettings.objects.get_or_create(organization=default_org)
        
        # Create a default device
        Device.objects.get_or_create(
            device_id='default_device',
            defaults={
                'organization': default_org,
                'device_name': 'Default Device',
                'location': 'Default Location',
                'is_active': True,
            }
        )
    
    # Assign all unassigned employees to default organization
    Employee.objects.filter(organization__isnull=True).update(organization=default_org)
    
    # Assign all unassigned attendance records to default organization
    AttendanceRecord.objects.filter(organization__isnull=True).update(organization=default_org)
    
    # Assign all unassigned live feed images to default organization
    LiveFeedImage.objects.filter(organization__isnull=True).update(organization=default_org)


def reverse_migration(apps, schema_editor):
    """Reverse the migration by setting organization to null (optional)."""
    # We don't delete the organization or remove assignments
    # as that would destroy data. This is intentionally a no-op.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0065_saas_multi_tenancy'),
    ]

    operations = [
        migrations.RunPython(create_default_organization, reverse_migration),
    ]
