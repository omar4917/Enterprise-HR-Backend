from datetime import date, timedelta
from decimal import Decimal
from django.db.models import Count, Q
from ..models import AttendanceRecord, Employee, SalaryAdjustment


def calculate_monthly_salary_adjustments(employee, year, month):
    """
    Calculate automatic bonus/fine for an employee for a specific month.
    
    Rules:
    - 3+ problematic days = 1 day's salary fine per 3 days (monthly_salary / 30)
    - 0 problematic days = 1000 BDT bonus
    - Problematic days: late, absent, half day, early leave, on leave (but not holidays/off days)
    - Multiple issues on same day don't stack (1 day = max 1 problematic day)
    
    Returns: (bonus_amount, fine_amount, problematic_days_count)
    """
    # Get attendance records for the month
    records = AttendanceRecord.objects.filter(
        employee=employee,
        date__year=year,
        date__month=month
    )
    
    # Count problematic days (excluding holidays and off days)
    problematic_days = 0
    total_working_days = 0
    
    for record in records:
        # Skip holidays and off days (these don't affect salary)
        if record.status in ['Holiday', 'Off Day']:
            continue
            
        total_working_days += 1
        
        # Check if this day has any problems
        has_problem = (
            record.is_late_indicator() or  # Late
            record.status in ['Absent', 'Half Day', 'Early Leave', 'On Leave']  # Other issues
        )
        
        if has_problem:
            problematic_days += 1
    
    # Calculate fine (every 3 problematic days = 1 day's salary)
    fine_amount = Decimal('0.00')
    if problematic_days >= 3:
        fine_groups = problematic_days // 3
        daily_salary = employee.monthly_salary / Decimal('30')
        fine_amount = daily_salary * fine_groups
    
    # Calculate bonus (no problematic days = 1000 BDT)
    bonus_amount = Decimal('0.00')
    if problematic_days == 0 and total_working_days > 0:
        bonus_amount = Decimal('1000.00')
    
    return bonus_amount, fine_amount, problematic_days


def process_monthly_salary_adjustments(year, month):
    """
    Process automatic salary adjustments for all employees for a given month.
    ONLY handles the 2 automatic rules: Late Fine & Perfect Bonus
    """
    month_date = date(year, month, 1)
    processed_count = 0
    
    for employee in Employee.objects.all():
        bonus_amount, fine_amount, late_days = calculate_monthly_salary_adjustments(
            employee, year, month
        )
        
        # Handle Perfect Attendance Bonus (0 problematic days = 1000 BDT)
        perfect_bonus_exists = SalaryAdjustment.objects.filter(
            employee=employee,
            month=month_date,
            reason="100% On Time Bonus",
            adjustment_type='bonus',
            is_automatic=True
        ).first()
        
        if bonus_amount > 0:
            if perfect_bonus_exists:
                # Update existing
                perfect_bonus_exists.amount = bonus_amount
                perfect_bonus_exists.comments = f"Perfect attendance - {late_days} problematic days"
                perfect_bonus_exists.save()
            else:
                # Create new
                SalaryAdjustment.objects.create(
                    employee=employee,
                    month=month_date,
                    reason="100% On Time Bonus",
                    adjustment_type='bonus',
                    amount=bonus_amount,
                    is_automatic=True,
                    comments=f"Perfect attendance - {late_days} problematic days"
                )
            processed_count += 1
        elif perfect_bonus_exists:
            # Remove bonus if no longer eligible
            perfect_bonus_exists.delete()
            processed_count += 1
        
        # Handle Attendance Issues Fine (3+ problematic days = 1 day's salary per 3 days)
        attendance_fine_exists = SalaryAdjustment.objects.filter(
            employee=employee,
            month=month_date,
            reason="Attendance Issues Fine",
            adjustment_type='fine',
            is_automatic=True
        ).first()
        
        if fine_amount > 0:
            fine_groups = late_days // 3
            daily_salary = employee.monthly_salary / Decimal('30')
            if attendance_fine_exists:
                # Update existing
                attendance_fine_exists.amount = fine_amount
                attendance_fine_exists.comments = f"{late_days} problematic days - {fine_groups} fine(s) of {daily_salary:.2f} BDT each"
                attendance_fine_exists.save()
            else:
                # Create new
                SalaryAdjustment.objects.create(
                    employee=employee,
                    month=month_date,
                    reason="Attendance Issues Fine",
                    adjustment_type='fine',
                    amount=fine_amount,
                    is_automatic=True,
                    comments=f"{late_days} problematic days - {fine_groups} fine(s) of {daily_salary:.2f} BDT each"
                )
            processed_count += 1
        elif attendance_fine_exists:
            # Remove fine if no longer applicable
            attendance_fine_exists.delete()
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
    # Include adjustments for ANY day of the month, not just 1st
    adjustments = SalaryAdjustment.objects.filter(
        employee=employee,
        month__year=year,
        month__month=month
    )
    bonuses = adjustments.filter(adjustment_type='bonus')
    fines = adjustments.filter(adjustment_type='fine')
    
    total_bonus = sum(b.amount for b in bonuses)
    total_fine = sum(f.amount for f in fines)
    
    # Calculate problematic days
    _, _, problematic_days = calculate_monthly_salary_adjustments(employee, year, month)
    
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
        'late_days': problematic_days,  # Now represents problematic days
        'bonuses': bonuses,
        'fines': fines,
        'all_adjustments': adjustments,
        'working_days': working_days
    }