"""
Management command to create dummy attendance records for testing multi-tenancy.
Run with: python manage.py create_dummy_attendance
"""

from django.core.management.base import BaseCommand
from attendance.models import Organization, Employee, AttendanceRecord, Shift
from datetime import date, time, datetime, timedelta
import random


class Command(BaseCommand):
    help = 'Create dummy attendance records for new organization employees'

    def handle(self, *args, **options):
        # Get the current month
        today = date.today()
        year = today.year
        month = today.month
        
        # Get active shift
        try:
            shift = Shift.objects.filter(is_active=True).first()
        except:
            shift = None

        statuses = ['Present', 'Late', 'Absent', 'On Leave']
        status_weights = [70, 15, 10, 5]  # Higher chance of Present

        created_records = 0
        orgs_processed = 0

        # Get organizations (excluding Default Organization if it has slug 'default')
        organizations = Organization.objects.filter(is_active=True).exclude(slug='default')

        self.stdout.write(f'\nGenerating attendance for {today.strftime("%B %Y")}...\n')

        for org in organizations:
            orgs_processed += 1
            employees = Employee.objects.filter(organization=org, is_active=True)
            
            if not employees.exists():
                self.stdout.write(f'  [!] No employees found for: {org.name}')
                continue
            
            self.stdout.write(f'  [+] {org.name} - {employees.count()} employees')

            # Generate records for current month up to today
            for day in range(1, today.day + 1):
                record_date = date(year, month, day)
                
                # Skip Fridays (Bangladesh weekend)
                if record_date.weekday() == 4:
                    continue
                
                for emp in employees:
                    # Check if record already exists
                    if AttendanceRecord.objects.filter(employee=emp, date=record_date).exists():
                        continue
                    
                    # Random status
                    status = random.choices(statuses, weights=status_weights, k=1)[0]
                    
                    # Generate times based on status (as datetime, not just time)
                    if status in ['Present', 'Late']:
                        if status == 'Late':
                            checkin_hour = random.randint(10, 11)
                            checkin_min = random.randint(0, 30)
                        else:
                            checkin_hour = random.randint(8, 9)
                            checkin_min = random.randint(0, 59)
                        
                        checkout_hour = random.randint(17, 19)
                        checkout_min = random.randint(0, 59)
                        
                        # Combine date + time into datetime
                        checkin_time = datetime(year, month, day, checkin_hour, checkin_min)
                        checkout_time = datetime(year, month, day, checkout_hour, checkout_min)
                    else:
                        checkin_time = None
                        checkout_time = None

                    AttendanceRecord.objects.create(
                        employee=emp,
                        organization=org,
                        date=record_date,
                        status=status,
                        checkin_time=checkin_time,
                        checkout_time=checkout_time,
                        shift=shift,
                        device_id='dummy_generator',
                    )
                    created_records += 1

            emp_count = employees.count()
            days = today.day
            self.stdout.write(f'      -> Created records for {days} days')

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS(f'Done! Created {created_records} attendance records'))
        self.stdout.write(self.style.SUCCESS(f'For {orgs_processed} organizations'))
        self.stdout.write(self.style.SUCCESS('=' * 50))
