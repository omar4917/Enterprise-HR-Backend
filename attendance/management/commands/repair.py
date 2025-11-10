from django.core.management.base import BaseCommand
from attendance.models import AttendanceRecord
from datetime import date


class Command(BaseCommand):
    help = "Convert any attendance records on Fridays to Off Day (one-time cleanup)"

    def handle(self, *args, **kwargs):
        updated = 0
        qs = AttendanceRecord.objects.filter(
            date__week_day=6
        )  # Django week_day: Sunday=1, Saturday=7 (DB dependent)
        # If your DB doesn't support date__week_day consistently, fallback to scanning all:
        if not qs.exists():
            qs = AttendanceRecord.objects.all()

        for r in qs:
            try:
                if r.date.weekday() == 4 and r.status != "Off Day":
                    r.status = "Off Day"
                    r.checkin_time = None
                    r.checkout_time = None
                    r.save(update_fields=["status", "checkin_time", "checkout_time"])
                    updated += 1
            except Exception:
                # skip malformed dates
                continue

        self.stdout.write(
            self.style.SUCCESS(f"Updated {updated} Friday records to Off Day")
        )
