import os
from datetime import datetime, date, timedelta
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone
import pytz

dhaka = pytz.timezone("Asia/Dhaka")


def dhaka_now():
    return timezone.now().astimezone(dhaka)


def employee_checkin_path(instance, filename):
    now = dhaka_now()
    today = now.strftime("%Y-%m-%d")
    timestamp = now.strftime("%H%M%S")
    ext = filename.split(".")[-1]
    new_filename = f"in_{today}_{timestamp}.{ext}"
    return os.path.join(
        "checkin_images", instance.employee.employee_id, today, new_filename
    )


def employee_checkout_path(instance, filename):
    now = dhaka_now()
    today = now.strftime("%Y-%m-%d")
    timestamp = now.strftime("%H%M%S")
    ext = filename.split(".")[-1]
    new_filename = f"out_{today}_{timestamp}.{ext}"
    return os.path.join(
        "checkout_images", instance.employee.employee_id, today, new_filename
    )


class Employee(models.Model):
    employee_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    department = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    designation = models.CharField(max_length=50)
    branch = models.CharField(max_length=50)
    employee_image = models.ImageField(
        upload_to="employee_photos/", null=True, blank=True
    )

    # Salary for bonus/fine calculations
    monthly_salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Monthly salary in BDT for bonus/fine calculations",
    )

    # 128-d face encoding for face_recognition (stored as JSON list of floats)
    face_encoding = models.JSONField(
        null=True,
        blank=True,
        help_text="128-d face encoding vector for face recognition",
    )

    def save(self, *args, **kwargs):
        """
        Save employee normally, then (if a photo exists and we don't yet have
        an encoding) try to generate and store a 128-d face encoding.

        This runs once per employee image; failures are silently ignored so
        admin UI remains usable even if face_recognition is missing.
        """
        super().save(*args, **kwargs)

        # Only attempt encoding if we have a photo and no encoding yet
        if self.employee_image and not self.face_encoding:
            try:
                from PIL import Image
                import numpy as np
                import face_recognition

                img = Image.open(self.employee_image.path).convert("RGB")
                img_np = np.array(img)
                locations = face_recognition.face_locations(img_np)

                if locations:
                    encoding = face_recognition.face_encodings(img_np, locations)[0]
                    self.face_encoding = encoding.tolist()
                    super().save(update_fields=["face_encoding"])
            except Exception:
                # Ignore encoding failures – admin can retry by clearing face_encoding
                pass

    def __str__(self):
        return f"{self.employee_id} - {self.name}"


class Shift(models.Model):
    """
    Single source of truth for shift thresholds. Create multiple shifts and mark exactly one active.
    """

    name = models.CharField(max_length=80, unique=True)
    shift_start = models.TimeField()
    shift_end = models.TimeField()
    half_day_hours = models.DecimalField(
        max_digits=4, decimal_places=2, default=Decimal("4.00")
    )
    present_hours = models.DecimalField(
        max_digits=4, decimal_places=2, default=Decimal("8.00")
    )
    allowed_late_minutes = models.PositiveIntegerField(
        default=0, help_text="Allowed minutes after shift start before flagged late"
    )
    enable_late_status = models.BooleanField(default=True)
    is_active = models.BooleanField(
        default=False, help_text="Only one shift should be active at a time"
    )

    class Meta:
        ordering = ("-is_active", "name")

    def __str__(self):
        return f"{self.name} {'(active)' if self.is_active else ''}"

    def save(self, *args, **kwargs):
        # Ensure only one active shift at a time (atomic)
        if self.is_active:
            from django.db import transaction

            with transaction.atomic():
                self.__class__.objects.filter(is_active=True).exclude(
                    pk=self.pk
                ).update(is_active=False)
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)


def get_active_shift():
    return Shift.objects.filter(is_active=True).first()


class AttendanceRecord(models.Model):
    """
    Stores checkin/checkout info and computed status.

    IMPORTANT:
      - Each record now has its own 'shift' snapshot.
      - If shift is empty on FIRST save, we copy the then-active shift and keep it.
      - Later global shift changes don't rewrite history.
    """

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    date = models.DateField()

    # Shift used to evaluate this record (can be edited manually later)
    shift = models.ForeignKey(
        Shift,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Shift used for this attendance day. "
        "If empty, falls back to the active shift.",
    )

    checkin_time = models.DateTimeField(null=True, blank=True)
    checkin_image = models.ImageField(
        upload_to=employee_checkin_path, null=True, blank=True
    )

    checkout_time = models.DateTimeField(null=True, blank=True)
    checkout_image = models.ImageField(
        upload_to=employee_checkout_path, null=True, blank=True
    )

    # which device sent the record (face terminal id)
    device_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Source device identifier (optional)",
    )

    status = models.CharField(
        max_length=20,
        choices=[
            ("Present", "Present"),
            ("Early Leave", "Early Leave"),
            ("Absent", "Absent"),
            ("Half Day", "Half Day"),
            ("On Leave", "On Leave"),
            ("Holiday", "Holiday"),
            ("Pending", "Pending"),
            ("Off Day", "Off Day"),
        ],
        null=True,
        blank=True,
    )

    # persisted timedelta: how long employee was late beyond allowed minutes (precision seconds)
    late_duration = models.DurationField(
        null=True,
        blank=True,
        help_text="Duration employee was late beyond allowed minutes",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-date", "-checkin_time")

    def __str__(self):
        ci = (
            self.checkin_time.astimezone(dhaka).strftime("%Y-%m-%d %I:%M %p")
            if self.checkin_time
            else "—"
        )
        co = (
            self.checkout_time.astimezone(dhaka).strftime("%Y-%m-%d %I:%M %p")
            if self.checkout_time
            else "—"
        )
        return f"{self.employee.employee_id} | IN: {ci} | OUT: {co}"

    @property
    def effective_shift(self):
        """
        Shift actually used for calculations for THIS record.
        Priority:
          1) self.shift (local / frozen / manually edited)
          2) current active shift (fallback only)
        """
        return self.shift or get_active_shift()

    def _active_shift(self):
        # Backwards-compat shim for existing logic calling this
        return self.effective_shift

    def _compute_late_duration(self, shift):
        """
        Precise, timezone-aware lateness calculation.

        Returns:
        - None if no checkin or no shift
        - timedelta(0) if within allowed window (not late)
        - positive timedelta = checkin_time - allowed_end if late (seconds-accurate)

        Rules:
        allowed_end = shift_start_dt + timedelta(minutes=shift.allowed_late_minutes)
        if checkin_time > allowed_end: late_duration = checkin_time - allowed_end (strict)
        if checkin_time == allowed_end: not late
        """
        if not self.checkin_time or not shift:
            return None

        # ensure both datetimes are in the same timezone (Dhaka)
        try:
            local_ci = self.checkin_time.astimezone(dhaka)
        except Exception:
            local_ci = self.checkin_time

        # build shift start datetime in same tz and same date
        shift_start_dt = datetime.combine(self.date, shift.shift_start)
        if shift_start_dt.tzinfo is None:
            shift_start_dt = dhaka.localize(shift_start_dt)
        else:
            shift_start_dt = shift_start_dt.astimezone(dhaka)

        allowed_minutes = int(shift.allowed_late_minutes or 0)
        allowed_end = shift_start_dt + timedelta(minutes=allowed_minutes)

        # Strict comparison: only times strictly greater than allowed_end are late
        if local_ci > allowed_end:
            return local_ci - allowed_end
        return timedelta(0)

    def _is_late(self, shift):
        """
        True only when computed late_duration is positive (strictly greater than zero seconds).
        """
        dur = self._compute_late_duration(shift)
        return bool(dur and dur.total_seconds() > 0)

    def is_late_indicator(self):
        """
        Returns True if employee was late (for UI indicators like exclamation marks).
        This is separate from status - used for visual indicators.
        """
        shift = self.effective_shift
        return self._is_late(shift) if shift else False

    def compute_status(self):
        """
        Computes status using THIS record's effective shift and populates self.late_duration.

        New Rules:
          - Absent if no checkin and no checkout
          - Pending if missing one timestamp (Late indicator shown separately)
          - When both exist, compute worked_hours:
              * Present if worked_hours >= present_hours (8+ hours)
              * Half Day if worked_hours >= half_day_hours (4+ hours)
              * Early Leave if worked_hours < half_day_hours
          - Late is tracked separately as an indicator, not a status
        """
        shift = self.effective_shift

        try:
            late_dur = self._compute_late_duration(shift)
        except Exception:
            late_dur = None
        self.late_duration = late_dur if late_dur is not None else None

        if not self.checkin_time and not self.checkout_time:
            return "Absent"

        if not self.checkin_time or not self.checkout_time:
            return "Pending"

        # both timestamps exist - prioritize work hours over lateness
        worked_hours = (self.checkout_time - self.checkin_time).total_seconds() / 3600.0

        if shift and worked_hours >= float(shift.present_hours):
            return "Present"

        if shift and worked_hours >= float(shift.half_day_hours):
            return "Half Day"

        return "Early Leave"

    def save(self, *args, **kwargs):
        """
        - On first save (new record) if no shift is set, freeze in the current active shift.
        - Preserve manual statuses: On Leave, Holiday, Off Day.
        - Otherwise recompute status + late_duration based on the record's effective shift.
        - Trigger salary recalculation when attendance changes
        """
        # If new record and no explicit shift, snapshot the current active shift
        if self.pk is None and self.shift is None:
            try:
                self.shift = get_active_shift()
            except Exception:
                self.shift = None

        manual_statuses = ["On Leave", "Holiday", "Off Day"]
        if self.status not in manual_statuses:
            computed = self.compute_status()
            # allow computed Late to be saved even though it's removed from manual dropdown
            self.status = computed if computed else self.status

        # Ensure late_duration persisted (a timedelta or None)
        if getattr(self, "late_duration", None) is None:
            try:
                self.late_duration = self._compute_late_duration(self.effective_shift)
            except Exception:
                self.late_duration = None

        super().save(*args, **kwargs)
        
        # Auto-recalculate salary adjustments when attendance changes
        self._trigger_salary_recalculation()
    
    def _trigger_salary_recalculation(self):
        """
        Automatically recalculate salary adjustments when attendance record changes
        """
        try:
            # Import here to avoid circular imports
            from django.apps import apps
            SalaryAdjustment = apps.get_model('attendance', 'SalaryAdjustment')
            
            # Recalculate for this employee's month
            from datetime import date
            month_date = date(self.date.year, self.date.month, 1)
            
            # Get current late days for this employee
            records = AttendanceRecord.objects.filter(
                employee=self.employee,
                date__year=self.date.year,
                date__month=self.date.month
            )
            
            late_days = 0
            total_working_days = 0
            
            for record in records:
                if record.status in ['Holiday', 'Off Day']:
                    continue
                total_working_days += 1
                
                # Only count late days for fine
                if record.is_late_indicator():
                    late_days += 1
            
            # Update automatic fine
            from decimal import Decimal
            fine_amount = Decimal('0.00')
            if late_days >= 3:
                fine_groups = late_days // 3
                daily_salary = self.employee.monthly_salary / Decimal('30')
                fine_amount = daily_salary * fine_groups
            
            attendance_fine = SalaryAdjustment.objects.filter(
                employee=self.employee,
                month=month_date,
                reason="Attendance Issues Fine",
                adjustment_type='fine',
                is_automatic=True
            ).first()
            
            if fine_amount > 0:
                if attendance_fine:
                    attendance_fine.amount = fine_amount
                    attendance_fine.comments = f"{late_days} late days - {fine_groups} fine(s) of {daily_salary:.2f} BDT each"
                    attendance_fine.save()
                else:
                    SalaryAdjustment.objects.create(
                        employee=self.employee,
                        month=month_date,
                        reason="Attendance Issues Fine",
                        adjustment_type='fine',
                        amount=fine_amount,
                        is_automatic=True,
                        comments=f"{late_days} late days - {fine_groups} fine(s) of {daily_salary:.2f} BDT each"
                    )
            elif attendance_fine:
                attendance_fine.delete()
            
            # Update automatic bonus (100% present + no late)
            bonus_amount = Decimal('0.00')
            all_present = all(r.status == 'Present' for r in records if r.status not in ['Holiday', 'Off Day'])
            if late_days == 0 and all_present and total_working_days > 0:
                bonus_amount = Decimal('1000.00')
            
            perfect_bonus = SalaryAdjustment.objects.filter(
                employee=self.employee,
                month=month_date,
                reason="100% On Time Bonus",
                adjustment_type='bonus',
                is_automatic=True
            ).first()
            
            if bonus_amount > 0:
                if perfect_bonus:
                    perfect_bonus.amount = bonus_amount
                    perfect_bonus.comments = f"100% Present + No Late Days"
                    perfect_bonus.save()
                else:
                    SalaryAdjustment.objects.create(
                        employee=self.employee,
                        month=month_date,
                        reason="100% On Time Bonus",
                        adjustment_type='bonus',
                        amount=bonus_amount,
                        is_automatic=True,
                        comments=f"100% Present + No Late Days"
                    )
            elif perfect_bonus:
                perfect_bonus.delete()
                
        except Exception as e:
            # Silently fail to avoid breaking attendance saves
            print(f"Salary recalculation failed: {e}")


class SalaryAdjustment(models.Model):
    """
    Employee salary adjustments - bonuses and fines in one model
    """
    ADJUSTMENT_TYPES = [
        ('bonus', 'Bonus'),
        ('fine', 'Fine'),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    adjustment_type = models.CharField(max_length=10, choices=ADJUSTMENT_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=200)
    date_created = models.DateField(auto_now_add=True)
    month = models.DateField(help_text="Month this adjustment applies to (YYYY-MM-01)")
    is_automatic = models.BooleanField(default=False, help_text="Auto-generated adjustment")
    comments = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ("-date_created",)
        unique_together = ("employee", "month", "reason", "adjustment_type")

    def __str__(self):
        sign = "+" if self.adjustment_type == 'bonus' else "-"
        return f"{self.employee.name} - {sign}{self.amount} BDT - {self.reason}"


class BulkHoliday(models.Model):
    """
    Bulk holiday management for multiple employees and date ranges
    """
    SCOPE_CHOICES = [
        ('all', 'All Employees'),
        ('department', 'Department'),
        ('designation', 'Designation'),
        ('custom', 'Selected Employees'),
    ]
    
    name = models.CharField(max_length=200, help_text="Holiday name (e.g., 'Eid Holiday', 'Project Completion Break')")
    start_date = models.DateField()
    end_date = models.DateField()
    scope = models.CharField(max_length=20, choices=SCOPE_CHOICES, default='all')
    is_active = models.BooleanField(default=True, help_text="Whether this holiday is currently active")
    
    # Filters for scope
    department = models.CharField(max_length=100, blank=True, null=True, help_text="Required if scope is 'department'")
    designation = models.CharField(max_length=50, blank=True, null=True, help_text="Required if scope is 'designation'")
    selected_employees = models.ManyToManyField(Employee, blank=True, help_text="Required if scope is 'custom'")
    
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=100, blank=True, null=True, help_text="Username who created this holiday")
    created_by_name = models.CharField(max_length=200, blank=True, null=True, help_text="Optional display name (e.g., 'Omar Khayam')")
    is_government = models.BooleanField(default=False, help_text="Whether this is a government holiday")
    
    class Meta:
        ordering = ('-created_at',)
    
    def __str__(self):
        return f"{self.name} ({self.start_date} to {self.end_date})"
    
    def get_affected_employees(self):
        """Get list of employees affected by this holiday"""
        if self.scope == 'all':
            return Employee.objects.all()
        elif self.scope == 'department':
            return Employee.objects.filter(department=self.department)
        elif self.scope == 'designation':
            return Employee.objects.filter(designation=self.designation)
        elif self.scope == 'custom':
            return self.selected_employees.all()
        return Employee.objects.none()
    
    def process_holiday_records(self):
        """Create attendance records for all affected employees and dates"""
        from datetime import timedelta
        
        if not self.is_active:
            return 0
            
        employees = self.get_affected_employees()
        current_date = self.start_date
        records_created = 0
        
        while current_date <= self.end_date:
            for employee in employees:
                # Check if record already exists
                existing = AttendanceRecord.objects.filter(
                    employee=employee,
                    date=current_date
                ).first()
                
                if not existing:
                    # Create new holiday record
                    AttendanceRecord.objects.create(
                        employee=employee,
                        date=current_date,
                        status='Holiday'
                    )
                    records_created += 1
                # Don't override existing attendance records (preserve overtime work)
            
            current_date += timedelta(days=1)
        
        return records_created
    
    def save(self, *args, **kwargs):
        """Auto-process on creation or when activated"""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Auto-process if active
        if self.is_active:
            self.process_holiday_records()
        else:
            # Remove records if deactivated
            self.remove_holiday_records()
    
    def remove_holiday_records(self):
        """Remove attendance records for this holiday"""
        from datetime import timedelta
        
        employees = self.get_affected_employees()
        current_date = self.start_date
        
        while current_date <= self.end_date:
            # Delete all holiday records for these dates
            records = AttendanceRecord.objects.filter(
                employee__in=employees,
                date=current_date,
                status='Holiday'
            )
            records.delete()
            current_date += timedelta(days=1)
    
    def delete(self, *args, **kwargs):
        """Override delete to also remove related attendance records"""
        from datetime import timedelta
        
        # Force delete all holiday records for this holiday's dates
        employees = list(self.get_affected_employees())
        current_date = self.start_date
        
        while current_date <= self.end_date:
            AttendanceRecord.objects.filter(
                employee__in=employees,
                date=current_date,
                status='Holiday'
            ).delete()
            current_date += timedelta(days=1)
        
        super().delete(*args, **kwargs)





# keep DashboardStub so admin dashboard entry works (non-managed)
class DashboardStub(models.Model):
    class Meta:
        managed = False
        verbose_name = "Attendance Dashboard"
        verbose_name_plural = "Attendance Dashboard"


class SalaryReportStub(models.Model):
    class Meta:
        managed = False
        verbose_name = "Salary Report"
        verbose_name_plural = "Salary Report"


class HolidayManagementStub(models.Model):
    class Meta:
        managed = False
        verbose_name = "Holiday Management"
        verbose_name_plural = "Holiday Management"



