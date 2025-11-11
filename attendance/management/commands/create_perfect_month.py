from django.core.management.base import BaseCommand
from datetime import datetime, date, timedelta
import pytz
from attendance.models import AttendanceRecord, Employee, Shift

class Command(BaseCommand):
    help = 'Create perfect attendance for Emp001 for November 2025'

    def handle(self, *args, **options):
        dhaka = pytz.timezone("Asia/Dhaka")
        
        # Get employee and shift
        emp = Employee.objects.get(employee_id="Emp001")
        shift = Shift.objects.filter(is_active=True).first()
        
        # Create perfect attendance for November 2025
        start_date = date(2025, 11, 1)
        end_date = date(2025, 11, 30)
        current_date = start_date
        created_count = 0
        
        while current_date <= end_date:
            # Skip Friday only (Friday=4)
            if current_date.weekday() != 4:
                
                # Delete existing record if any
                AttendanceRecord.objects.filter(employee=emp, date=current_date).delete()
                
                # Create perfect attendance record
                checkin_time = dhaka.localize(datetime.combine(current_date, datetime.strptime("08:00", "%H:%M").time()))
                checkout_time = dhaka.localize(datetime.combine(current_date, datetime.strptime("17:30", "%H:%M").time()))
                
                AttendanceRecord.objects.create(
                    employee=emp,
                    date=current_date,
                    checkin_time=checkin_time,
                    checkout_time=checkout_time,
                    shift=shift,
                    status="Present"
                )
                
                created_count += 1
                self.stdout.write(f"Created perfect attendance for {current_date}")
            
            current_date += timedelta(days=1)
        
        self.stdout.write(self.style.SUCCESS(f'Created {created_count} perfect attendance records for {emp.name}'))
        self.stdout.write(self.style.SUCCESS('Employee should now be eligible for 1000 BDT perfect attendance bonus!'))