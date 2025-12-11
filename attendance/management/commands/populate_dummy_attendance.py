from django.core.management.base import BaseCommand
from attendance.models import Employee, AttendanceRecord, dhaka
from django.utils import timezone
import random
from datetime import timedelta, datetime

class Command(BaseCommand):
    help = 'Populates the database with 20 dummy attendance records'

    def handle(self, *args, **kwargs):
        employees = list(Employee.objects.all())
        if not employees:
            self.stdout.write(self.style.ERROR('No employees found. Please add employees first.'))
            return

        self.stdout.write('Generating 20 dummy attendance records...')

        for i in range(20):
            employee = random.choice(employees)
            
            # Random date within last 30 days
            days_ago = random.randint(0, 30)
            date = timezone.now().date() - timedelta(days=days_ago)
            
            # Random checkin between 08:00 and 11:00
            checkin_hour = random.randint(8, 10)
            checkin_minute = random.randint(0, 59)
            checkin_time = datetime.combine(date, datetime.min.time()) + timedelta(hours=checkin_hour, minutes=checkin_minute)
            checkin_time = dhaka.localize(checkin_time)
            
            # Random checkout between 16:00 and 20:00
            checkout_hour = random.randint(16, 19)
            checkout_minute = random.randint(0, 59)
            checkout_time = datetime.combine(date, datetime.min.time()) + timedelta(hours=checkout_hour, minutes=checkout_minute)
            checkout_time = dhaka.localize(checkout_time)
            
            # Create record
            record = AttendanceRecord.objects.create(
                employee=employee,
                date=date,
                checkin_time=checkin_time,
                checkout_time=checkout_time,
                device_id=f"dummy_device_{random.randint(1, 5)}",
                status="Present" # Let model re-calculate if needed, or set initial
            )
            
            self.stdout.write(f"Created record for {employee.name} on {date}")

        self.stdout.write(self.style.SUCCESS('Successfully generated 20 dummy attendance records.'))
