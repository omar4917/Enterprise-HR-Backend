from datetime import date, timedelta
from decimal import Decimal
from django.db.models import Count, Q
from ..models import AttendanceRecord, Employee, SalaryAdjustment


def calculate_monthly_salary_adjustments(employee, year, month):
    """
    Calculate automatic bonus/fine for an employee for a specific month.
    
    Rules:
    - 3+ late days = 1000 BDT fine per 3 late days
    - 0 late days = 1000 BDT bonus
    
    Returns: (bonus_amount, fine_amount, late_days_count)
    """
    # Get attendance records for the month
    records = AttendanceRecord.objects.filter(
        employee=employee,
        date__year=year,
        date__month=month
    )
    
    # Count late days (excluding weekends, holidays, leaves)
    late_days = 0
    total_working_days = 0
    
    for record in records:
        # Skip non-working days
        if record.status in ['Holiday', 'Off Day', 'On Leave']:
            continue
            
        total_working_days += 1
        
        # Check if late
        if record.is_late_indicator():
            late_days += 1
    
    # Calculate fine (every 3 late days = 1000 BDT fine)
    fine_amount = Decimal('0.00')
    if late_days >= 3:
        fine_groups = late_days // 3
        fine_amount = Decimal('1000.00') * fine_groups
    
    # Calculate bonus (no late days = 1000 BDT)
    bonus_amount = Decimal('0.00')
    if late_days == 0 and total_working_days > 0:
        bonus_amount = Decimal('1000.00')
    
    return bonus_amount, fine_amount, late_days


def process_monthly_salary_adjustments(year, month):
    """
    Process automatic salary adjustments for all employees for a given month.
    Creates Bonus and Fine records automatically.
    """
    month_date = date(year, month, 1)
    processed_count = 0
    
    for employee in Employee.objects.all():
        bonus_amount, fine_amount, late_days = calculate_monthly_salary_adjustments(
            employee, year, month
        )
        
        # Create or update automatic bonus if applicable
        if bonus_amount > 0:
            try:
                # Try to get existing record
                adjustment = SalaryAdjustment.objects.get(
                    employee=employee,
                    month=month_date,
                    reason="100% On Time Bonus",
                    adjustment_type='bonus',
                    is_automatic=True
                )
                # Update existing record
                adjustment.amount = bonus_amount
                adjustment.comments = f"Perfect attendance for {month_date.strftime('%B %Y')} - No late days"
                adjustment.save()
                processed_count += 1
            except SalaryAdjustment.DoesNotExist:
                # Create new record
                SalaryAdjustment.objects.create(
                    employee=employee,
                    month=month_date,
                    reason="100% On Time Bonus",
                    adjustment_type='bonus',
                    amount=bonus_amount,
                    is_automatic=True,
                    comments=f"Perfect attendance for {month_date.strftime('%B %Y')} - No late days"
                )
                processed_count += 1
        
        # Create or update automatic fine if applicable
        if fine_amount > 0:
            fine_groups = late_days // 3
            try:
                # Try to get existing record
                adjustment = SalaryAdjustment.objects.get(
                    employee=employee,
                    month=month_date,
                    reason="Late Days Fine",
                    adjustment_type='fine',
                    is_automatic=True
                )
                # Update existing record
                adjustment.amount = fine_amount
                adjustment.comments = f"{late_days} late days in {month_date.strftime('%B %Y')} - {fine_groups} fine(s) of 1000 BDT each"
                adjustment.save()
                processed_count += 1
            except SalaryAdjustment.DoesNotExist:
                # Create new record
                SalaryAdjustment.objects.create(
                    employee=employee,
                    month=month_date,
                    reason="Late Days Fine",
                    adjustment_type='fine',
                    amount=fine_amount,
                    is_automatic=True,
                    comments=f"{late_days} late days in {month_date.strftime('%B %Y')} - {fine_groups} fine(s) of 1000 BDT each"
                )
                processed_count += 1
    
    return processed_count


def get_employee_salary_summary(employee, year, month):
    """
    Get complete salary summary for an employee for a specific month.
    
    Returns:
    {
        'base_salary': Decimal,
        'total_bonus': Decimal,
        'total_fine': Decimal,
        'net_adjustment': Decimal,
        'late_days': int,
        'bonuses': QuerySet,
        'fines': QuerySet
    }
    """
    month_date = date(year, month, 1)
    
    # Get ALL adjustments for the month (manual + automatic)
    adjustments = SalaryAdjustment.objects.filter(employee=employee, month=month_date)
    bonuses = adjustments.filter(adjustment_type='bonus')
    fines = adjustments.filter(adjustment_type='fine')
    
    total_bonus = sum(b.amount for b in bonuses)
    total_fine = sum(f.amount for f in fines)
    
    # Calculate late days
    _, _, late_days = calculate_monthly_salary_adjustments(employee, year, month)
    
    # Use monthly salary as base
    working_days = AttendanceRecord.objects.filter(
        employee=employee,
        date__year=year,
        date__month=month
    ).exclude(
        status__in=['Holiday', 'Off Day', 'On Leave']
    ).count()
    
    base_salary = employee.monthly_salary
    net_adjustment = total_bonus - total_fine
    
    return {
        'base_salary': base_salary,
        'total_bonus': total_bonus,
        'total_fine': total_fine,
        'net_adjustment': net_adjustment,
        'late_days': late_days,
        'bonuses': bonuses,
        'fines': fines,
        'all_adjustments': adjustments,
        'working_days': working_days
    }