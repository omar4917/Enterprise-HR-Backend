from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from django.contrib.auth import get_user_model

from attendance.models import PayrollAdjustment
from attendance.utils import compute_and_create_adjustments_for_month
from hr.models import AttendanceRecord  # adjust to your actual model path

User = get_user_model()


def first_and_last_day_of_prev_month(ref_date=None):
    d = ref_date or timezone.localdate()
    first_of_this = d.replace(day=1)
    last_of_prev = first_of_this - timedelta(days=1)
    first_of_prev = last_of_prev.replace(day=1)
    return first_of_prev, last_of_prev


class Command(BaseCommand):
    help = "Process monthly attendance fines and bonuses"

    def add_arguments(self, parser):
        parser.add_argument('--for-month', type=str,
                            help="Month to process in YYYY-MM format. If omitted, processes previous month.")

    def handle(self, *args, **options):
        arg = options.get('for_month')
        if arg:
            y, m = map(int, arg.split('-'))
            start = date(y, m, 1)
            # compute last day
            if m == 12:
                end = date(y, 12, 31)
            else:
                end = date(y, m+1, 1) - timedelta(days=1)
        else:
            start, end = first_and_last_day_of_prev_month()

        employees = User.objects.filter(is_active=True)  # refine as needed
        # salary lookup callable

        def salary_lookup(emp):
            # example: employee.profile.monthly_salary
            return getattr(getattr(emp, 'profile', None), 'monthly_salary', 0) or 0

        created = compute_and_create_adjustments_for_month(
            start, end, employees, AttendanceRecord, salary_lookup
        )
        self.stdout.write(self.style.SUCCESS(f"Processed {len(created)} adjustments for {start} - {end}"))
