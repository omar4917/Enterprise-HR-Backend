import os
from django.core.management.base import BaseCommand
from django.core.files import File
from django.utils import timezone
from attendance.models import Employee, AttendanceRecord
from datetime import datetime


class Command(BaseCommand):
    help = "Simulate attendance by reading images from Test/IN and Test/OUT folders"  # noqa

    TEST_DIR = r"C:\Users\BARA BD\Desktop\Attendence Control Project\Test"
    CHECKIN_DIR = os.path.join(TEST_DIR, "IN")
    CHECKOUT_DIR = os.path.join(TEST_DIR, "OUT")

    def handle(self, *args, **kwargs):
        self.process_folder(self.CHECKIN_DIR, event_type="IN")
        self.process_folder(self.CHECKOUT_DIR, event_type="OUT")

    def process_folder(self, folder_path, event_type):
        if not os.path.exists(folder_path):
            self.stdout.write(
                self.style.ERROR(f"Folder {folder_path} does not exist")
            )  # noqa
            return

        for filename in os.listdir(folder_path):
            if not filename.lower().endswith((".jpg", ".png", ".jpeg")):
                continue

            employee_id, _ = os.path.splitext(filename)
            try:
                employee = Employee.objects.get(employee_id=employee_id)
            except Employee.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"Employee {employee_id} not found in DB") # noqa
                )
                continue

            filepath = os.path.join(folder_path, filename)
            # Make timestamp timezone-aware
            timestamp = timezone.make_aware(
                datetime.fromtimestamp(os.path.getmtime(filepath)),
                timezone.get_current_timezone(),
            )

            # Get or create AttendanceRecord for this employee for this date
            record, created = AttendanceRecord.objects.get_or_create(
                employee=employee, date=timestamp.date()
            )

            if event_type == "IN":
                record.checkin_time = timestamp
                with open(filepath, "rb") as f:
                    record.checkin_image.save(filename, File(f), save=False)
            else:
                record.checkout_time = timestamp
                with open(filepath, "rb") as f:
                    record.checkout_image.save(filename, File(f), save=False)

            record.save()
            action = "created" if created else "updated"
            self.stdout.write(
                self.style.SUCCESS(
                    f"{event_type} record {action} for {employee_id} at {timestamp}"  # noqa
                )
            )
