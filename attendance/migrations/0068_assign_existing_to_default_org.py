# Data migration to assign existing records to default organization
# Ensures backwards compatibility for existing data

from django.db import migrations


def assign_existing_to_default_org(apps, schema_editor):
    """Assign existing records to the default organization."""
    Organization = apps.get_model('attendance', 'Organization')
    BulkHoliday = apps.get_model('attendance', 'BulkHoliday')
    Shift = apps.get_model('attendance', 'Shift')
    SalaryStatisticDefault = apps.get_model('attendance', 'SalaryStatisticDefault')
    CompanyInfo = apps.get_model('attendance', 'CompanyInfo')
    VoiceSetting = apps.get_model('attendance', 'VoiceSetting')
    ContextSetting = apps.get_model('attendance', 'ContextSetting')
    ModeratorLabel = apps.get_model('attendance', 'ModeratorLabel')
    
    # Get or create default organization
    default_org, created = Organization.objects.get_or_create(
        slug='default',
        defaults={
            'name': 'Default Organization',
            'is_active': True,
        }
    )
    
    # Assign unassigned records to default org
    BulkHoliday.objects.filter(organization__isnull=True).update(organization=default_org)
    Shift.objects.filter(organization__isnull=True).update(organization=default_org)
    SalaryStatisticDefault.objects.filter(organization__isnull=True).update(organization=default_org)
    CompanyInfo.objects.filter(organization__isnull=True).update(organization=default_org)
    VoiceSetting.objects.filter(organization__isnull=True).update(organization=default_org)
    ContextSetting.objects.filter(organization__isnull=True).update(organization=default_org)
    ModeratorLabel.objects.filter(organization__isnull=True).update(organization=default_org)
    
    print(f"  -> Assigned existing records to: {default_org.name}")


def reverse_assignment(apps, schema_editor):
    """Reverse by setting organization to null."""
    BulkHoliday = apps.get_model('attendance', 'BulkHoliday')
    Shift = apps.get_model('attendance', 'Shift')
    SalaryStatisticDefault = apps.get_model('attendance', 'SalaryStatisticDefault')
    CompanyInfo = apps.get_model('attendance', 'CompanyInfo')
    VoiceSetting = apps.get_model('attendance', 'VoiceSetting')
    ContextSetting = apps.get_model('attendance', 'ContextSetting')
    ModeratorLabel = apps.get_model('attendance', 'ModeratorLabel')
    
    # Set all back to null
    BulkHoliday.objects.all().update(organization=None)
    Shift.objects.all().update(organization=None)
    SalaryStatisticDefault.objects.all().update(organization=None)
    CompanyInfo.objects.all().update(organization=None)
    VoiceSetting.objects.all().update(organization=None)
    ContextSetting.objects.all().update(organization=None)
    ModeratorLabel.objects.all().update(organization=None)


class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0067_add_organization_to_models'),
    ]

    operations = [
        migrations.RunPython(assign_existing_to_default_org, reverse_assignment),
    ]
