"""
Seed script: Creates 3 organizations, 5 employees each, shifts, and attendance records.
Run with: python manage.py shell < seed_data.py
"""
import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "attendance_project.settings")
django.setup()

from datetime import datetime, date, timedelta, time
from decimal import Decimal
from django.contrib.auth.models import User
from attendance.models import (
    Organization, OrganizationUser, Employee, Shift, AttendanceRecord
)
import pytz
import random

dhaka = pytz.timezone("Asia/Dhaka")

print("=" * 60)
print("SEEDING DATABASE")
print("=" * 60)

# ============================================================
# 1. CREATE 3 ORGANIZATIONS
# ============================================================
orgs_data = [
    {
        "name": "TechNova Solutions",
        "slug": "technova-solutions",
        "email": "admin@technova.com",
        "phone": "+8801711111111",
        "address": "House 12, Road 5, Dhanmondi, Dhaka-1205",
        "website": "https://technova.com.bd",
        "tin": "TIN-20240001",
        "bin": "BIN-20240001",
        "founder": "Rahim Ahmed",
        "max_employees": 50,
        "max_devices": 5,
    },
    {
        "name": "GreenLeaf Garments",
        "slug": "greenleaf-garments",
        "email": "admin@greenleaf.com",
        "phone": "+8801722222222",
        "address": "BSCIC Industrial Area, Tongi, Gazipur",
        "website": "https://greenleaf.com.bd",
        "tin": "TIN-20240002",
        "bin": "BIN-20240002",
        "founder": "Fatima Begum",
        "max_employees": 200,
        "max_devices": 10,
    },
    {
        "name": "ByteCraft Digital",
        "slug": "bytecraft-digital",
        "email": "admin@bytecraft.io",
        "phone": "+8801733333333",
        "address": "Level 5, Navana Tower, Gulshan-1, Dhaka-1212",
        "website": "https://bytecraft.io",
        "tin": "TIN-20240003",
        "bin": "BIN-20240003",
        "founder": "Kamal Hossain",
        "max_employees": 30,
        "max_devices": 3,
    },
]

organizations = []
for od in orgs_data:
    org, created = Organization.objects.get_or_create(slug=od["slug"], defaults=od)
    organizations.append(org)
    status = "CREATED" if created else "EXISTS"
    print(f"  [{status}] Organization: {org.name}")

# ============================================================
# 2. CREATE ADMIN USERS FOR EACH ORG + ORG USERS
# ============================================================
admin_credentials = []

# Make existing 'admin' user a super_admin
admin_user = User.objects.filter(username="admin").first()
if admin_user:
    ou, _ = OrganizationUser.objects.get_or_create(
        user=admin_user,
        defaults={"role": "super_admin", "organization": None}
    )
    print(f"  [OK] Super admin: admin / admin123")

org_admin_data = [
    {"username": "technova_admin", "email": "admin@technova.com", "password": "admin123", "org_idx": 0},
    {"username": "greenleaf_admin", "email": "admin@greenleaf.com", "password": "admin123", "org_idx": 1},
    {"username": "bytecraft_admin", "email": "admin@bytecraft.io", "password": "admin123", "org_idx": 2},
]

for ad in org_admin_data:
    user, created = User.objects.get_or_create(
        username=ad["username"],
        defaults={
            "email": ad["email"],
            "is_staff": True,
            "is_active": True,
        }
    )
    if created:
        user.set_password(ad["password"])
        user.save()

    org = organizations[ad["org_idx"]]
    ou, _ = OrganizationUser.objects.get_or_create(
        user=user,
        defaults={
            "organization": org,
            "role": "org_main_admin",
        }
    )
    admin_credentials.append({
        "org": org.name,
        "username": ad["username"],
        "password": ad["password"],
        "role": "org_main_admin",
    })
    print(f"  [OK] Org admin: {ad['username']} -> {org.name}")

# ============================================================
# 3. CREATE SHIFTS FOR EACH ORG
# ============================================================
for org in organizations:
    shift, created = Shift.objects.get_or_create(
        organization=org,
        name="Morning Shift",
        defaults={
            "shift_start": time(9, 0),
            "shift_end": time(18, 0),
            "half_day_hours": Decimal("4.00"),
            "present_hours": Decimal("8.00"),
            "allowed_late_minutes": 15,
            "absent_after_minutes": 60,
            "is_active": True,
        }
    )
    status = "CREATED" if created else "EXISTS"
    print(f"  [{status}] Shift: Morning Shift -> {org.name}")

# ============================================================
# 4. CREATE 5 EMPLOYEES PER ORG (15 total)
# ============================================================
employees_per_org = {
    0: [  # TechNova Solutions
        {"employee_id": "TN-001", "name": "Arif Rahman", "email": "arif@technova.com", "department": "Engineering", "designation": "Senior Developer", "monthly_salary": Decimal("85000.00"), "phone": "01811001001"},
        {"employee_id": "TN-002", "name": "Nusrat Jahan", "email": "nusrat@technova.com", "department": "Engineering", "designation": "Frontend Developer", "monthly_salary": Decimal("65000.00"), "phone": "01811001002"},
        {"employee_id": "TN-003", "name": "Shakil Hasan", "email": "shakil@technova.com", "department": "Design", "designation": "UI/UX Designer", "monthly_salary": Decimal("55000.00"), "phone": "01811001003"},
        {"employee_id": "TN-004", "name": "Taslima Akter", "email": "taslima@technova.com", "department": "HR", "designation": "HR Manager", "monthly_salary": Decimal("70000.00"), "phone": "01811001004"},
        {"employee_id": "TN-005", "name": "Imran Khan", "email": "imran@technova.com", "department": "Engineering", "designation": "DevOps Engineer", "monthly_salary": Decimal("80000.00"), "phone": "01811001005"},
    ],
    1: [  # GreenLeaf Garments
        {"employee_id": "GL-001", "name": "Abdur Rahim", "email": "rahim@greenleaf.com", "department": "Production", "designation": "Floor Manager", "monthly_salary": Decimal("45000.00"), "phone": "01822001001"},
        {"employee_id": "GL-002", "name": "Sabina Yasmin", "email": "sabina@greenleaf.com", "department": "Quality", "designation": "QC Inspector", "monthly_salary": Decimal("30000.00"), "phone": "01822001002"},
        {"employee_id": "GL-003", "name": "Jamal Uddin", "email": "jamal@greenleaf.com", "department": "Production", "designation": "Line Supervisor", "monthly_salary": Decimal("35000.00"), "phone": "01822001003"},
        {"employee_id": "GL-004", "name": "Ruma Khatun", "email": "ruma@greenleaf.com", "department": "Admin", "designation": "Office Assistant", "monthly_salary": Decimal("22000.00"), "phone": "01822001004"},
        {"employee_id": "GL-005", "name": "Hasan Ali", "email": "hasan@greenleaf.com", "department": "Warehouse", "designation": "Store Keeper", "monthly_salary": Decimal("25000.00"), "phone": "01822001005"},
    ],
    2: [  # ByteCraft Digital
        {"employee_id": "BC-001", "name": "Farhan Labib", "email": "farhan@bytecraft.io", "department": "Engineering", "designation": "Lead Developer", "monthly_salary": Decimal("95000.00"), "phone": "01833001001"},
        {"employee_id": "BC-002", "name": "Shorna Das", "email": "shorna@bytecraft.io", "department": "Marketing", "designation": "Digital Marketing Lead", "monthly_salary": Decimal("60000.00"), "phone": "01833001002"},
        {"employee_id": "BC-003", "name": "Rayhan Kabir", "email": "rayhan@bytecraft.io", "department": "Engineering", "designation": "Backend Developer", "monthly_salary": Decimal("75000.00"), "phone": "01833001003"},
        {"employee_id": "BC-004", "name": "Mehzabin Islam", "email": "mehzabin@bytecraft.io", "department": "Design", "designation": "Creative Director", "monthly_salary": Decimal("80000.00"), "phone": "01833001004"},
        {"employee_id": "BC-005", "name": "Tanvir Haque", "email": "tanvir@bytecraft.io", "department": "Engineering", "designation": "QA Engineer", "monthly_salary": Decimal("50000.00"), "phone": "01833001005"},
    ],
}

all_employees = []
for org_idx, emp_list in employees_per_org.items():
    org = organizations[org_idx]
    for ed in emp_list:
        emp, created = Employee.objects.get_or_create(
            employee_id=ed["employee_id"],
            defaults={
                "organization": org,
                "name": ed["name"],
                "email": ed["email"],
                "department": ed["department"],
                "designation": ed["designation"],
                "monthly_salary": ed["monthly_salary"],
                "phone": ed["phone"],
                "is_active": True,
                "hire_date": date(2024, random.randint(1, 6), random.randint(1, 28)),
            }
        )
        all_employees.append(emp)
        status = "CREATED" if created else "EXISTS"
        print(f"  [{status}] Employee: {emp.employee_id} - {emp.name} ({org.name})")

# ============================================================
# 5. CREATE 7-10 ATTENDANCE RECORDS PER EMPLOYEE
# ============================================================
print("\nCreating attendance records...")

# Use recent working days (last 2 weeks, excluding Fridays which are weekends in BD)
today = date(2026, 2, 10)
working_days = []
d = today - timedelta(days=20)
while d <= today:
    if d.weekday() != 4:  # Skip Friday (BD weekend)
        working_days.append(d)
    d += timedelta(days=1)

# Take last 10 working days
working_days = working_days[-12:]

records_created = 0
for emp in all_employees:
    num_records = random.randint(7, 10)
    selected_days = random.sample(working_days, min(num_records, len(working_days)))
    selected_days.sort()

    for day in selected_days:
        # Randomize check-in time (some on time, some late)
        hour = 9
        minute = random.choice([0, 0, 0, 5, 10, 15, 20, 30, 45])  # Mostly on time
        if random.random() < 0.2:  # 20% chance of being late
            hour = random.choice([9, 10])
            minute = random.randint(20, 55)

        checkin_dt = dhaka.localize(datetime(day.year, day.month, day.day, hour, minute, 0))

        # Checkout: 8-9 hours later, some early leaves
        work_hours = random.choice([4, 6, 8, 8, 8, 8, 9, 9, 8.5, 7])
        checkout_dt = checkin_dt + timedelta(hours=work_hours)

        # Check for existing record
        existing = AttendanceRecord.objects.filter(employee=emp, date=day).exists()
        if not existing:
            AttendanceRecord.objects.create(
                organization=emp.organization,
                employee=emp,
                date=day,
                checkin_time=checkin_dt,
                checkout_time=checkout_dt,
            )
            records_created += 1

print(f"  [DONE] Created {records_created} attendance records")

# ============================================================
# SUMMARY
# ============================================================
print("\n" + "=" * 60)
print("SEED COMPLETE!")
print("=" * 60)
print(f"\nOrganizations: {Organization.objects.count()}")
print(f"Employees:     {Employee.objects.count()}")
print(f"Shifts:        {Shift.objects.count()}")
print(f"Attendance:    {AttendanceRecord.objects.count()}")
print(f"Users:         {User.objects.count()}")

print("\n" + "=" * 60)
print("LOGIN CREDENTIALS")
print("=" * 60)
print(f"\n{'Role':<20} {'Username':<20} {'Password':<12} {'Organization'}")
print("-" * 80)
print(f"{'Super Admin':<20} {'admin':<20} {'admin123':<12} {'All Organizations'}")
for cred in admin_credentials:
    print(f"{cred['role']:<20} {cred['username']:<20} {cred['password']:<12} {cred['org']}")

print("\nDjango Admin URL: http://localhost:8000/admin/")
print("Laravel URL:      http://127.0.0.1:8001")
print("=" * 60)
