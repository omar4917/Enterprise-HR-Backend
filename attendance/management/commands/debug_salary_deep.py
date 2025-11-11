from django.core.management.base import BaseCommand
from datetime import date
from decimal import Decimal
from ...models import Employee, SalaryAdjustment
from ...utils.salary_helpers import calculate_monthly_salary_adjustments, process_monthly_salary_adjustments


class Command(BaseCommand):
    help = 'Deep debug salary calculations'

    def handle(self, *args, **options):
        current_month = date.today().month
        current_year = date.today().year
        
        self.stdout.write("=== DEEP SALARY DEBUG ===\n")
        
        # Test 1: Check month format issue
        self.stdout.write("1. TESTING MONTH FORMAT ISSUE:")
        test_dates = [
            date(current_year, current_month, 1),  # 1st of month
            date(current_year, current_month, 15), # 15th of month
        ]
        
        for test_date in test_dates:
            adjustments = SalaryAdjustment.objects.filter(month=test_date)
            self.stdout.write(f"   Month {test_date}: {adjustments.count()} adjustments found")
        
        # Test 2: Check calculation vs database
        self.stdout.write("\n2. CALCULATION VS DATABASE:")
        for emp in Employee.objects.all()[:2]:  # Test first 2 employees
            bonus, fine, late_days = calculate_monthly_salary_adjustments(emp, current_year, current_month)
            
            self.stdout.write(f"\n   {emp.name} ({emp.employee_id}):")
            self.stdout.write(f"   - Calculated: Late={late_days}, Fine={fine}, Bonus={bonus}")
            
            # Check what's in database
            month_date = date(current_year, current_month, 1)
            db_adjustments = SalaryAdjustment.objects.filter(
                employee=emp,
                month=month_date
            )
            
            for adj in db_adjustments:
                self.stdout.write(f"   - DB: {adj.adjustment_type} = {adj.amount} ({adj.reason}) Auto={adj.is_automatic}")
        
        # Test 3: Force update
        self.stdout.write("\n3. FORCING UPDATE:")
        processed = process_monthly_salary_adjustments(current_year, current_month)
        self.stdout.write(f"   Processed: {processed} adjustments")
        
        # Test 4: Check again after update
        self.stdout.write("\n4. AFTER UPDATE:")
        for emp in Employee.objects.all()[:2]:
            month_date = date(current_year, current_month, 1)
            db_adjustments = SalaryAdjustment.objects.filter(
                employee=emp,
                month=month_date
            )
            
            self.stdout.write(f"\n   {emp.name}:")
            for adj in db_adjustments:
                self.stdout.write(f"   - {adj.adjustment_type}: {adj.amount} BDT ({adj.reason})")
        
        # Test 5: Manual adjustment test
        self.stdout.write("\n5. MANUAL ADJUSTMENT TEST:")
        emp = Employee.objects.first()
        
        # Try different month formats
        test_months = [
            date(current_year, current_month, 1),   # 1st
            date(current_year, current_month, 15),  # 15th
            date(current_year, current_month, 28),  # 28th
        ]
        
        for i, month_test in enumerate(test_months):
            manual_adj = SalaryAdjustment.objects.create(
                employee=emp,
                adjustment_type='bonus',
                amount=Decimal(f'{(i+1)*100}.00'),  # 100, 200, 300
                reason=f'Test Manual {i+1}',
                month=month_test,
                is_automatic=False,
                comments=f'Test with month={month_test}'
            )
            self.stdout.write(f"   Created: {manual_adj}")
        
        # Check what shows up
        all_adjustments = SalaryAdjustment.objects.filter(employee=emp)
        self.stdout.write(f"\n   All adjustments for {emp.name}:")
        for adj in all_adjustments:
            self.stdout.write(f"   - {adj.month} | {adj.adjustment_type}: {adj.amount} ({adj.reason})")