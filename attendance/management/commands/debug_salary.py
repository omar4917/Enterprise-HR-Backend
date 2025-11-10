from django.core.management.base import BaseCommand
from datetime import date
from ...models import Employee, SalaryAdjustment
from ...utils.salary_helpers import calculate_monthly_salary_adjustments


class Command(BaseCommand):
    help = 'Debug salary calculations'

    def handle(self, *args, **options):
        current_month = date.today().month
        current_year = date.today().year
        
        for emp in Employee.objects.all():
            bonus, fine, late_days = calculate_monthly_salary_adjustments(emp, current_year, current_month)
            
            self.stdout.write(f"\n--- {emp.name} ({emp.employee_id}) ---")
            self.stdout.write(f"Late Days: {late_days}")
            self.stdout.write(f"Expected Fine: {fine}")
            self.stdout.write(f"Expected Bonus: {bonus}")
            
            # Check existing adjustments
            adjustments = SalaryAdjustment.objects.filter(
                employee=emp,
                month=date(current_year, current_month, 1)
            )
            
            for adj in adjustments:
                self.stdout.write(f"DB: {adj.adjustment_type} - {adj.amount} - {adj.reason}")