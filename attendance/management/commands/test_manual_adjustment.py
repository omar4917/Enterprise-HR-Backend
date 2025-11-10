from django.core.management.base import BaseCommand
from datetime import date
from decimal import Decimal
from ...models import Employee, SalaryAdjustment


class Command(BaseCommand):
    help = 'Test manual salary adjustment'

    def handle(self, *args, **options):
        # Get first employee
        emp = Employee.objects.first()
        if not emp:
            self.stdout.write("No employees found")
            return
            
        current_month = date.today().replace(day=1)
        
        # Create manual bonus
        bonus = SalaryAdjustment.objects.create(
            employee=emp,
            adjustment_type='bonus',
            amount=Decimal('500.00'),
            reason='Manual Test Bonus',
            month=current_month,
            is_automatic=False,
            comments='Test manual bonus entry'
        )
        
        self.stdout.write(f"Created manual bonus: {bonus}")
        
        # Check all adjustments for this employee
        adjustments = SalaryAdjustment.objects.filter(
            employee=emp,
            month=current_month
        )
        
        self.stdout.write(f"\nAll adjustments for {emp.name}:")
        for adj in adjustments:
            self.stdout.write(f"- {adj.adjustment_type}: {adj.amount} BDT ({adj.reason}) - Auto: {adj.is_automatic}")
            
        # Calculate totals
        total_bonus = sum(a.amount for a in adjustments.filter(adjustment_type='bonus'))
        total_fine = sum(a.amount for a in adjustments.filter(adjustment_type='fine'))
        
        self.stdout.write(f"\nTotals: Bonus={total_bonus}, Fine={total_fine}")