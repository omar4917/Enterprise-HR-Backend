from django.core.management.base import BaseCommand
from attendance.models import Employee, AttendanceRecord, Organization, Shift, LiveFeedImage, Device, SalaryStatistic
from django.conf import settings
from datetime import date, datetime, timedelta
from decimal import Decimal
import random
import shutil
import os
import pytz

dhaka = pytz.timezone("Asia/Dhaka")


class Command(BaseCommand):
    help = 'Reset all employees and create fresh test data for all organizations'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("=== RESETTING EMPLOYEE DATA ==="))
        
        # 1. Delete all employees (cascade will delete attendance, salary stats, etc.)
        emp_count = Employee.objects.count()
        Employee.objects.all().delete()
        self.stdout.write(f"Deleted {emp_count} employees (and their related data)")
        
        # 2. Delete all live feed images
        live_count = LiveFeedImage.objects.count()
        LiveFeedImage.objects.all().delete()
        self.stdout.write(f"Deleted {live_count} live feed images")
        
        # 3. Delete all existing devices
        device_count = Device.objects.count()
        Device.objects.all().delete()
        self.stdout.write(f"Deleted {device_count} devices")
        
        # 4. Clear media folders
        media_root = settings.MEDIA_ROOT
        folders_to_clear = ['checkin_images', 'checkout_images', 'livefeed_images', 'employee_photos']
        
        for folder in folders_to_clear:
            folder_path = os.path.join(media_root, folder)
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path, ignore_errors=True)
                os.makedirs(folder_path, exist_ok=True)
                self.stdout.write(f"Cleared folder: {folder}")
        
        # 5. Get all organizations
        organizations = Organization.objects.filter(is_active=True)
        if not organizations.exists():
            self.stdout.write(self.style.ERROR("No active organizations found!"))
            return
        
        # 6. Get active shift
        shift = Shift.objects.filter(is_active=True).first()
        if not shift:
            shift = Shift.objects.first()
        
        if not shift:
            self.stdout.write(self.style.ERROR("No shift found! Creating default shift..."))
            shift = Shift.objects.create(
                name="Default Shift",
                shift_start=datetime.strptime("09:00", "%H:%M").time(),
                shift_end=datetime.strptime("18:00", "%H:%M").time(),
                is_active=True
            )
        
        self.stdout.write(f"Using shift: {shift.name} ({shift.shift_start} - {shift.shift_end})")
        
        # Sample employee names
        first_names = ["Ahmed", "Mohammad", "Fatima", "Aisha", "Omar", "Yusuf", "Khadija", "Hassan", 
                       "Zainab", "Ibrahim", "Maryam", "Ali", "Sara", "Khalid", "Noor", "Bilal",
                       "Amina", "Tariq", "Layla", "Hamza", "Safiya", "Umar", "Hana", "Imran"]
        last_names = ["Rahman", "Islam", "Khan", "Ahmed", "Hossain", "Uddin", "Akter", "Begum",
                      "Chowdhury", "Miah", "Ali", "Haque", "Karim", "Sultana", "Khatun", "Aktar"]
        departments = ["IT", "HR", "Finance", "Operations", "Sales", "Marketing", "Admin"]
        designations = ["Manager", "Executive", "Officer", "Analyst", "Developer", "Coordinator", "Assistant"]
        
        # Device locations for variation
        device_locations = [
            ("Main Entrance", "main-gate"),
            ("Back Gate", "back-gate"),
            ("Office Floor", "office"),
            ("Reception", "reception"),
            ("Lobby", "lobby"),
        ]
        
        total_employees = 0
        total_attendance = 0
        total_devices = 0
        total_salary_stats = 0
        
        # Current month/year for salary statistics
        today = date.today()
        current_month = today.month
        current_year = today.year
        # Also create for previous month
        if current_month == 1:
            prev_month, prev_year = 12, current_year - 1
        else:
            prev_month, prev_year = current_month - 1, current_year
        
        for org in organizations:
            # Create 1-3 devices per organization
            num_devices = random.randint(1, 3)
            org_devices = []
            
            for i in range(num_devices):
                location_name, location_code = device_locations[i % len(device_locations)]
                device_id = f"{org.slug[:3].upper()}-DEV-{str(i+1).zfill(2)}"
                device_name = f"{org.name} - {location_name}"
                
                device = Device.objects.create(
                    organization=org,
                    device_id=device_id,
                    device_name=device_name,
                    location=location_name,
                    is_active=True
                )
                org_devices.append(device)
                total_devices += 1
                self.stdout.write(f"  Created device: {device_id} - {location_name}")
            
            # Random number of employees per org (3-10)
            num_employees = random.randint(3, 10)
            self.stdout.write(f"\nCreating {num_employees} employees for: {org.name}")
            
            for i in range(num_employees):
                first = random.choice(first_names)
                last = random.choice(last_names)
                name = f"{first} {last}"
                
                emp_id = f"{org.slug[:3].upper()}-{str(i+1).zfill(3)}"
                monthly_salary = Decimal(random.randint(25000, 100000))
                
                employee = Employee.objects.create(
                    organization=org,
                    employee_id=emp_id,
                    name=name,
                    email=f"{first.lower()}.{last.lower()}.{emp_id.lower()}@{org.slug}.com",
                    department=random.choice(departments),
                    designation=random.choice(designations),
                    phone=f"+880{random.randint(1300000000, 1999999999)}",
                    monthly_salary=monthly_salary,
                    is_active=True,
                    hire_date=date.today() - timedelta(days=random.randint(30, 365))
                )
                total_employees += 1
                
                # Create salary statistics for current and previous month
                for month, year in [(current_month, current_year), (prev_month, prev_year)]:
                    basic_salary = monthly_salary * Decimal("0.60")  # 60% basic
                    house_rent = monthly_salary * Decimal("0.20")    # 20% house rent
                    medical = monthly_salary * Decimal("0.10")       # 10% medical
                    conveyance = monthly_salary * Decimal("0.05")    # 5% conveyance
                    food = monthly_salary * Decimal("0.05")          # 5% food
                    
                    working_days = random.randint(22, 26)
                    attended_days = random.randint(18, working_days)
                    
                    SalaryStatistic.objects.create(
                        employee=employee,
                        month=month,
                        year=year,
                        basic_salary=basic_salary,
                        house_rent=house_rent,
                        medical_allowance=medical,
                        conveyance_allowance=conveyance,
                        food_allowance=food,
                        gross_salary=monthly_salary,
                        working_days=working_days,
                        weekends=8,
                        leave_days=random.randint(0, 2),
                        holidays=random.randint(1, 3),
                        attended_days=attended_days,
                        payable=monthly_salary - Decimal(random.randint(0, 1000)),
                        use_default=True
                    )
                    total_salary_stats += 1
                
                # Create attendance records for last 7 days
                for days_ago in range(7):
                    record_date = date.today() - timedelta(days=days_ago)
                    
                    # Skip weekends (Friday/Saturday in Bangladesh)
                    if record_date.weekday() in [4, 5]:  # Friday=4, Saturday=5
                        continue
                    
                    # Randomly pick a device for this attendance
                    selected_device = random.choice(org_devices)
                    
                    # 80% chance of attendance
                    if random.random() < 0.8:
                        # Calculate check-in time based on shift
                        shift_hour = shift.shift_start.hour
                        shift_minute = shift.shift_start.minute
                        
                        # Random late by 0-30 minutes
                        late_minutes = random.randint(0, 30) if random.random() < 0.3 else 0
                        
                        checkin_dt = datetime.combine(record_date, shift.shift_start)
                        checkin_dt = checkin_dt + timedelta(minutes=late_minutes)
                        checkin_dt = dhaka.localize(checkin_dt)
                        
                        # Checkout 8-9 hours later
                        work_hours = random.randint(8, 9)
                        checkout_dt = checkin_dt + timedelta(hours=work_hours, minutes=random.randint(0, 30))
                        
                        # Determine status
                        if late_minutes > shift.allowed_late_minutes:
                            status = "Late" if shift.enable_late_status else "Present"
                        else:
                            status = "Present"
                        
                        AttendanceRecord.objects.create(
                            organization=org,
                            employee=employee,
                            shift=shift,
                            date=record_date,
                            checkin_time=checkin_dt,
                            checkout_time=checkout_dt,
                            status=status,
                            late_duration=timedelta(minutes=late_minutes) if late_minutes > 0 else None,
                            device_id=selected_device.device_id
                        )
                        total_attendance += 1
                    else:
                        # Absent - still associate with a device
                        AttendanceRecord.objects.create(
                            organization=org,
                            employee=employee,
                            shift=shift,
                            date=record_date,
                            status="Absent",
                            device_id=selected_device.device_id
                        )
                        total_attendance += 1
                
                self.stdout.write(f"  Created: {employee.employee_id} - {employee.name}")
        
        self.stdout.write(self.style.SUCCESS(f"\n=== DONE ==="))
        self.stdout.write(self.style.SUCCESS(f"Created {total_devices} devices"))
        self.stdout.write(self.style.SUCCESS(f"Created {total_employees} employees"))
        self.stdout.write(self.style.SUCCESS(f"Created {total_salary_stats} salary statistics"))
        self.stdout.write(self.style.SUCCESS(f"Created {total_attendance} attendance records"))

