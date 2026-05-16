from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, date, datetime, time
import random

from attendance.models import (
    Organization, Employee, Shift, Device, AttendanceRecord,
    IntegrationSetting, VoiceSetting, TextMessageSetting,
    SalaryStatisticDefault, OrganizationSettings, OrganizationUser
)
from django.contrib.auth.models import User
import pytz

class Command(BaseCommand):
    help = 'Seeds the database with initial dummy data for testing.'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting database seeding...")

        # Create Superuser if not exists
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin')
            self.stdout.write(self.style.SUCCESS("Created superuser admin"))

        # Skip if data already exists to prevent duplication on multiple deploys
        if Employee.objects.exists():
            self.stdout.write(self.style.WARNING("Database already contains employees. Skipping seed."))
            return

        dhaka_tz = pytz.timezone('Asia/Dhaka')
        today = timezone.localtime(timezone.now(), dhaka_tz).date()

        # 1. Create Organizations
        org1, _ = Organization.objects.get_or_create(
            name="Tech Innovators Ltd",
            slug="tech-innovators",
            defaults={'email': 'contact@techinnovators.com', 'is_active': True, 'max_employees': 50}
        )
        org2, _ = Organization.objects.get_or_create(
            name="Global Logistics",
            slug="global-logistics",
            defaults={'email': 'hr@globallogistics.com', 'is_active': True, 'max_employees': 100}
        )
        self.stdout.write(self.style.SUCCESS("Created Organizations"))

        # Assign admin user to org1
        user = User.objects.get(username='admin')
        OrganizationUser.objects.get_or_create(user=user, organization=org1, role='org_admin')

        # 2. Configure Global Settings
        IntegrationSetting.objects.get_or_create(pk=1, defaults={'fcm_server_key': 'DUMMY_KEY'})
        VoiceSetting.objects.get_or_create(pk=1, defaults={'default_language': 'en-US', 'name_format': 'full'})
        TextMessageSetting.objects.get_or_create(pk=1, defaults={'checkin_text': 'Welcome {name}', 'checkout_text': 'Goodbye {name}'})
        
        # 3. Create Shifts
        shift1, _ = Shift.objects.get_or_create(
            name="Morning Shift",
            defaults={
                'shift_start': time(9, 0),
                'shift_end': time(17, 0),
                'present_hours': 8.0,
                'half_day_hours': 4.0,
                'allowed_late_minutes': 15,
                'is_active': True
            }
        )
        shift2, _ = Shift.objects.get_or_create(
            name="Evening Shift",
            defaults={
                'shift_start': time(14, 0),
                'shift_end': time(22, 0),
                'present_hours': 8.0,
                'half_day_hours': 4.0,
                'allowed_late_minutes': 10,
                'is_active': True
            }
        )
        self.stdout.write(self.style.SUCCESS("Created Shifts"))

        # 4. Create Devices
        Device.objects.get_or_create(device_id="DEV-001", defaults={'device_name': 'Main Entrance', 'organization': org1, 'is_active': True})
        Device.objects.get_or_create(device_id="DEV-002", defaults={'device_name': 'Back Door', 'organization': org1, 'is_active': True})
        Device.objects.get_or_create(device_id="DEV-003", defaults={'device_name': 'Warehouse Gate', 'organization': org2, 'is_active': True})
        self.stdout.write(self.style.SUCCESS("Created Devices"))

        # 5. Create Employees
        employees_data = [
            {"id": "EMP001", "name": "Omar Khayam", "dept": "Engineering", "desig": "Lead Developer", "org": org1, "salary": 80000},
            {"id": "EMP002", "name": "Ayesha Rahman", "dept": "Engineering", "desig": "Backend Dev", "org": org1, "salary": 60000},
            {"id": "EMP003", "name": "Kamrul Hasan", "dept": "HR", "desig": "HR Manager", "org": org1, "salary": 50000},
            {"id": "EMP004", "name": "Sajid Islam", "dept": "Support", "desig": "Support Agent", "org": org1, "salary": 30000},
            {"id": "EMP005", "name": "Nadia Begum", "dept": "Sales", "desig": "Sales Executive", "org": org1, "salary": 45000},
            
            {"id": "LOG001", "name": "David Smith", "dept": "Operations", "desig": "Fleet Manager", "org": org2, "salary": 70000},
            {"id": "LOG002", "name": "Maria Garcia", "dept": "Operations", "desig": "Dispatcher", "org": org2, "salary": 40000},
        ]

        employee_objs = []
        for data in employees_data:
            emp, created = Employee.objects.get_or_create(
                employee_id=data["id"],
                defaults={
                    'name': data["name"],
                    'department': data["dept"],
                    'designation': data["desig"],
                    'organization': data["org"],
                    'monthly_salary': data["salary"],
                    'is_active': True
                }
            )
            if created:
                employee_objs.append(emp)
        self.stdout.write(self.style.SUCCESS(f"Created {len(employee_objs)} Employees"))

        # 6. Generate Attendance Records for the last 5 days
        attendance_count = 0
        for i in range(5):
            record_date = today - timedelta(days=i)
            # Skip Fridays (weekend)
            if record_date.weekday() == 4:
                continue

            for emp in employee_objs:
                # 10% chance of absence
                if random.random() < 0.1:
                    continue

                # Generate checkin time (around shift start)
                active_shift = Shift.objects.filter(name="Morning Shift").first() or shift1
                start_dt = datetime.combine(record_date, active_shift.shift_start)
                start_dt = dhaka_tz.localize(start_dt)
                
                # Random late up to 30 mins, or early up to 15 mins
                offset_mins = random.randint(-15, 30)
                checkin_time = start_dt + timedelta(minutes=offset_mins)

                # Checkout time (around 8 hours later)
                work_hours = random.uniform(7.5, 9.0)
                checkout_time = checkin_time + timedelta(hours=work_hours)

                # Determine status
                status = "Present"
                if offset_mins > active_shift.allowed_late_minutes:
                    pass # Will auto-compute late logic

                AttendanceRecord.objects.get_or_create(
                    employee=emp,
                    date=record_date,
                    defaults={
                        'checkin_time': checkin_time,
                        'checkout_time': checkout_time,
                        'status': status,
                        'shift': active_shift
                    }
                )
                attendance_count += 1

        self.stdout.write(self.style.SUCCESS(f"Generated {attendance_count} Attendance Records"))
        self.stdout.write(self.style.SUCCESS("Database seeding completed successfully!"))
