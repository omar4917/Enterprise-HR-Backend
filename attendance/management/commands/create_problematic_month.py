from django.core.management.base import BaseCommand
from datetime import datetime, date, timedelta
import pytz
from attendance.models import AttendanceRecord, Employee, Shift

class Command(BaseCommand):
    help = 'Create problematic attendance for Emp006 for November 2025'

    def handle(self, *args, **options):
        dhaka = pytz.timezone("Asia/Dhaka")
        
        # Get employee and shift
        emp = Employee.objects.get(employee_id="Emp006")
        shift = Shift.objects.filter(is_active=True).first()
        
        # Create attendance for November 2025
        start_date = date(2025, 11, 1)
        end_date = date(2025, 11, 30)
        current_date = start_date
        created_count = 0
        problem_days = 0
        
        while current_date <= end_date:
            # Skip Friday only (Friday=4)
            if current_date.weekday() != 4:
                
                # Delete existing record if any
                AttendanceRecord.objects.filter(employee=emp, date=current_date).delete()
                
                # Create exactly 3 late days for 1 fine
                if problem_days < 3 and current_date.day % 7 == 0:  # Every 7th working day
                    # Late arrivals only
                    checkin_time = dhaka.localize(datetime.combine(current_date, datetime.strptime("08:30", "%H:%M").time()))
                    checkout_time = dhaka.localize(datetime.combine(current_date, datetime.strptime("17:30", "%H:%M").time()))
                    status = "Present"
                    
                    problem_days += 1
                    self.stdout.write(f"Created late day {problem_days}: {current_date} - Late but Present")
                else:
                    # Normal working day
                    checkin_time = dhaka.localize(datetime.combine(current_date, datetime.strptime("08:00", "%H:%M").time()))
                    checkout_time = dhaka.localize(datetime.combine(current_date, datetime.strptime("17:30", "%H:%M").time()))
                    status = "Present"
                
                AttendanceRecord.objects.create(
                    employee=emp,
                    date=current_date,
                    checkin_time=checkin_time,
                    checkout_time=checkout_time,
                    shift=shift,
                    status=status
                )
                
                created_count += 1
            
            current_date += timedelta(days=1)
        
        self.stdout.write(self.style.SUCCESS(f'Created {created_count} attendance records for {emp.name}'))
        self.stdout.write(self.style.SUCCESS(f'Including {problem_days} late days - should get 1 fine (3÷3=1)'))