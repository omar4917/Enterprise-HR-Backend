from django.core.management.base import BaseCommand
from datetime import date, datetime, timedelta
from decimal import Decimal
import random

from ...models import Employee, AttendanceRecord, Shift, dhaka_now


class Command(BaseCommand):
    help = 'Create dummy attendance data for current month'

    def add_arguments(self, parser):
        parser.add_argument('--month', type=int, default=date.today().month)
        parser.add_argument('--year', type=int, default=date.today().year)

    def handle(self, *args, **options):
        month = options['month']
        year = options['year']
        
        # Create dummy employees if none exist
        if Employee.objects.count() == 0:
            self.create_dummy_employees()
        
        # Create dummy shift if none exists
        if not Shift.objects.filter(is_active=True).exists():
            self.create_dummy_shift()
        
        # Create attendance records
        self.create_attendance_records(year, month)
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created dummy attendance for {year}-{month:02d}')
        )

    def create_dummy_employees(self):
        employees_data = [
            {'id': 'EMP001', 'name': 'John Doe', 'dept': 'IT', 'salary': 30000},
            {'id': 'EMP002', 'name': 'Jane Smith', 'dept': 'HR', 'salary': 25000},
            {'id': 'EMP003', 'name': 'Mike Johnson', 'dept': 'IT', 'salary': 35000},
            {'id': 'EMP004', 'name': 'Sarah Wilson', 'dept': 'Finance', 'salary': 28000},
            {'id': 'EMP005', 'name': 'David Brown', 'dept': 'IT', 'salary': 32000},
        ]
        
        for emp_data in employees_data:
            Employee.objects.get_or_create(
                employee_id=emp_data['id'],
                defaults={
                    'name': emp_data['name'],
                    'email': f"{emp_data['id'].lower()}@company.com",
                    'department': emp_data['dept'],
                    'phone': '01700000000',
                    'designation': 'Developer' if emp_data['dept'] == 'IT' else 'Officer',
                    'branch': 'Main Office',
                    'monthly_salary': Decimal(str(emp_data['salary']))
                }
            )
        
        self.stdout.write('Created dummy employees')

    def create_dummy_shift(self):
        Shift.objects.get_or_create(
            name='Regular Shift',
            defaults={
                'shift_start': datetime.strptime('09:00', '%H:%M').time(),
                'shift_end': datetime.strptime('18:00', '%H:%M').time(),
                'half_day_hours': Decimal('4.00'),
                'present_hours': Decimal('8.00'),
                'allowed_late_minutes': 15,
                'enable_late_status': True,
                'is_active': True
            }
        )
        
        self.stdout.write('Created dummy shift')

    def create_attendance_records(self, year, month):
        employees = Employee.objects.all()
        
        # Get all days in the month
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        
        current_date = start_date
        
        while current_date <= end_date:
            # Skip Fridays (weekday 4)
            if current_date.weekday() == 4:
                current_date += timedelta(days=1)
                continue
            
            for emp in employees:
                # Create different attendance patterns
                attendance_type = self.get_attendance_pattern(emp, current_date)
                
                if attendance_type == 'absent':
                    # No record for absent
                    pass
                elif attendance_type == 'holiday':
                    AttendanceRecord.objects.get_or_create(
                        employee=emp,
                        date=current_date,
                        defaults={'status': 'Holiday'}
                    )
                elif attendance_type == 'leave':
                    AttendanceRecord.objects.get_or_create(
                        employee=emp,
                        date=current_date,
                        defaults={'status': 'On Leave'}
                    )
                else:
                    # Create normal attendance with random times
                    checkin_time, checkout_time = self.generate_times(current_date, attendance_type)
                    
                    record, created = AttendanceRecord.objects.get_or_create(
                        employee=emp,
                        date=current_date,
                        defaults={
                            'checkin_time': checkin_time,
                            'checkout_time': checkout_time
                        }
                    )
                    
                    # Force save to trigger late calculation
                    if created:
                        record.save()
            
            current_date += timedelta(days=1)

    def get_attendance_pattern(self, emp, current_date):
        """Generate different attendance patterns for variety"""
        # Some employees are more punctual than others
        if emp.employee_id == 'EMP001':  # John - very punctual
            return random.choices(['on_time', 'late'], weights=[90, 10])[0]
        elif emp.employee_id == 'EMP002':  # Jane - perfect attendance
            return 'on_time'
        elif emp.employee_id == 'EMP003':  # Mike - often late
            return random.choices(['on_time', 'late', 'absent'], weights=[60, 30, 10])[0]
        elif emp.employee_id == 'EMP004':  # Sarah - mixed
            return random.choices(['on_time', 'late', 'leave'], weights=[70, 20, 10])[0]
        else:  # David - regular
            return random.choices(['on_time', 'late', 'absent'], weights=[80, 15, 5])[0]

    def generate_times(self, current_date, attendance_type):
        """Generate realistic check-in and check-out times"""
        import pytz
        dhaka = pytz.timezone("Asia/Dhaka")
        
        base_checkin = datetime.combine(current_date, datetime.strptime('09:00', '%H:%M').time())
        base_checkin = dhaka.localize(base_checkin)
        
        if attendance_type == 'late':
            # Late by 20-120 minutes
            late_minutes = random.randint(20, 120)
            checkin_time = base_checkin + timedelta(minutes=late_minutes)
        else:
            # On time or slightly early
            early_minutes = random.randint(-10, 15)
            checkin_time = base_checkin + timedelta(minutes=early_minutes)
        
        # Checkout time - usually 8-9 hours after checkin
        work_hours = random.uniform(7.5, 9.5)
        checkout_time = checkin_time + timedelta(hours=work_hours)
        
        return checkin_time, checkout_time