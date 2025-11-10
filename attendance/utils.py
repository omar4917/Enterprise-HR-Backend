from decimal import Decimal
from datetime import date
from django.conf import settings
from django.db import transaction
from .models import PayrollAdjustment

POLICY = getattr(settings, "ATTENDANCE_POLICY", {})


def compute_employee_month_late_counts(attendance_qs, start_date, end_date):
    """
    attendance_qs: queryset filtered for employee and date range, with boolean field .is_late
    returns integer count of days late in range
    """
    # ensure attendance records are one per day and have is_late
    return attendance_qs.filter(is_late=True).values("date").distinct().count()


def compute_and_create_adjustments_for_month(
    start_date, end_date, employees_qs, attendance_model, salary_lookup
):
    """
    start_date: date object first day of month
    end_date: date object last day of month
    employees_qs: queryset of employees to process
    attendance_model: Django model class for attendance records
    salary_lookup: callable(employee) -> Decimal monthly_salary OR function to compute per-day value
    """
    late_threshold = int(POLICY.get("LATE_THRESHOLD_FOR_FINE", 3))
    fine_amount_days = Decimal(POLICY.get("FINE_AMOUNT", 1.0))
    bonus_enabled = bool(POLICY.get("BONUS_IF_NO_LATE", True))
    bonus_amount = Decimal(POLICY.get("BONUS_AMOUNT", 0))

    created = []
    with transaction.atomic():
        for emp in employees_qs:
            qs = attendance_model.objects.filter(
                employee=emp, date__gte=start_date, date__lte=end_date
            )
            late_days = compute_employee_month_late_counts(qs, start_date, end_date)

            # Fine: if late_days >= threshold -> create PayrollAdjustment (FINE)
            if late_threshold > 0 and late_days >= late_threshold:
                # Decide amount: here we convert "days of salary" into currency using salary_lookup
                monthly_salary = Decimal(salary_lookup(emp))
                per_day_salary = monthly_salary / Decimal(
                    30
                )  # adjust to your payroll rules
                amount_to_deduct = (per_day_salary * fine_amount_days).quantize(
                    Decimal("0.01")
                )
                PayrollAdjustment.objects.update_or_create(
                    employee=emp,
                    month=start_date,
                    adjustment_type="FINE",
                    defaults={
                        "amount": amount_to_deduct,
                        "reason": f"{late_days} late days in {start_date.strftime('%B %Y')}",
                        "applied": False,
                        "metadata": {"late_days": late_days},
                    },
                )
                created.append(("FINE", emp.pk, amount_to_deduct))

            # Bonus: if zero late days -> create bonus
            if bonus_enabled and late_days == 0:
                amount = bonus_amount
                if amount > 0:
                    PayrollAdjustment.objects.update_or_create(
                        employee=emp,
                        month=start_date,
                        adjustment_type="BONUS",
                        defaults={
                            "amount": amount,
                            "reason": f"No late days in {start_date.strftime('%B %Y')}",
                            "applied": False,
                            "metadata": {"late_days": late_days},
                        },
                    )
                    created.append(("BONUS", emp.pk, amount))

    return created
