"""
Data fix script to update organization_id for employees and attendance records.
Run this via Django shell: python manage.py shell < fix_org_data.py
"""
from attendance.models import Employee, AttendanceRecord, Organization

# Get or create Default Organization
default_org, created = Organization.objects.get_or_create(
    name="Default Organization",
    defaults={"is_active": True}
)

print(f"Default Organization ID: {default_org.id}")

# 1. Update employees without organization_id to Default Organization
employees_without_org = Employee.objects.filter(organization__isnull=True)
count_emp = employees_without_org.count()
print(f"Found {count_emp} employees without organization")

if count_emp > 0:
    employees_without_org.update(organization=default_org)
    print(f"Updated {count_emp} employees to Default Organization")

# 2. Update attendance records to match their employee's organization
records_to_update = AttendanceRecord.objects.filter(
    organization__isnull=True,
    employee__organization__isnull=False
)
count_rec = records_to_update.count()
print(f"Found {count_rec} attendance records with null org but employee has org")

updated = 0
for rec in AttendanceRecord.objects.select_related('employee__organization').filter(organization__isnull=True):
    if rec.employee and rec.employee.organization:
        rec.organization = rec.employee.organization
        rec.save(update_fields=['organization'])
        updated += 1

print(f"Updated {updated} attendance records with employee's organization")

# 3. Also update records where employee org differs from record org
mismatched = AttendanceRecord.objects.select_related('employee__organization').exclude(
    organization=None
).exclude(
    employee__organization=None
).filter(
    employee__organization__isnull=False
)

mismatch_count = 0
for rec in mismatched:
    if rec.employee and rec.employee.organization and rec.organization != rec.employee.organization:
        mismatch_count += 1

print(f"Found {mismatch_count} records where employee org differs from record org (not updating these)")

print("\n=== Summary ===")
print(f"Employees fixed: {count_emp}")
print(f"Records fixed: {updated}")
print("Done!")
