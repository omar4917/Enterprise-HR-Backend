from django.core.management.base import BaseCommand
from attendance.models import Employee, AttendanceRecord, Organization


class Command(BaseCommand):
    help = 'Fix organization_id on attendance records to match their employee organization'

    def handle(self, *args, **options):
        # Get Default Organization
        try:
            default_org = Organization.objects.get(name="Default Organization")
            self.stdout.write(f"Default Organization ID: {default_org.id}")
        except Organization.DoesNotExist:
            self.stdout.write(self.style.ERROR("Default Organization not found!"))
            return

        # 1. Update employees without organization
        emp_count = Employee.objects.filter(organization__isnull=True).update(organization=default_org)
        self.stdout.write(f"Employees updated to Default Org: {emp_count}")

        # 2. Update attendance records with null org to use employee's org
        records_null_org = AttendanceRecord.objects.select_related('employee__organization').filter(
            organization__isnull=True,
            employee__organization__isnull=False
        )
        null_count = records_null_org.count()
        self.stdout.write(f"Records with null org (employee has org): {null_count}")
        
        updated = 0
        for rec in records_null_org:
            rec.organization = rec.employee.organization
            rec.save(update_fields=['organization'])
            updated += 1
        self.stdout.write(f"Updated {updated} records with null org")

        # 3. Sync records where org differs from employee org
        all_records = AttendanceRecord.objects.select_related('employee__organization').filter(
            employee__organization__isnull=False
        )
        
        synced = 0
        for rec in all_records:
            if rec.organization_id != rec.employee.organization_id:
                rec.organization = rec.employee.organization
                rec.save(update_fields=['organization'])
                synced += 1
        
        self.stdout.write(f"Synced {synced} records to match employee organization")
        self.stdout.write(self.style.SUCCESS(f"Done! Total fixed: {updated + synced}"))
