from django.core.management.base import BaseCommand
from datetime import date
from ...models import AttendanceRecord, Employee


class Command(BaseCommand):
    help = 'Test late calculation for attendance records'

    def handle(self, *args, **options):
        records = AttendanceRecord.objects.filter(
            date__month=date.today().month,
            date__year=date.today().year
        )[:5]
        
        for record in records:
            self.stdout.write(f"\n--- {record.employee.name} - {record.date} ---")
            self.stdout.write(f"Check-in: {record.checkin_time}")
            self.stdout.write(f"Check-out: {record.checkout_time}")
            self.stdout.write(f"Status: {record.status}")
            self.stdout.write(f"Late Duration: {record.late_duration}")
            self.stdout.write(f"Is Late Indicator: {record.is_late_indicator()}")
            
            # Force recalculate
            record.save()
            record.refresh_from_db()
            
            self.stdout.write(f"After save - Status: {record.status}")
            self.stdout.write(f"After save - Late Duration: {record.late_duration}")
            self.stdout.write(f"After save - Is Late: {record.is_late_indicator()}")