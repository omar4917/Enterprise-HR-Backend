# Core Django and Python imports
import os
from datetime import datetime, date, timedelta
from decimal import Decimal

# Django framework imports
from django.conf import settings
from django.db import models
from django.utils import timezone
import pytz
from django.db.models.signals import post_save
from django.dispatch import receiver

# Timezone configuration for Bangladesh
dhaka = pytz.timezone("Asia/Dhaka")


def dhaka_now():
    """Get current datetime in Dhaka timezone"""
    return timezone.now().astimezone(dhaka)


def employee_checkin_path(instance, filename):
    """Generate organized file path for checkin images"""
    now = dhaka_now()
    today = now.strftime("%Y-%m-%d")
    timestamp = now.strftime("%H%M%S")
    ext = filename.split(".")[-1]
    new_filename = f"in_{today}_{timestamp}.{ext}"
    return os.path.join(
        "checkin_images", instance.employee.employee_id, today, new_filename
    )


def employee_checkout_path(instance, filename):
    """Generate organized file path for checkout images"""
    now = dhaka_now()
    today = now.strftime("%Y-%m-%d")
    timestamp = now.strftime("%H%M%S")
    ext = filename.split(".")[-1]
    new_filename = f"out_{today}_{timestamp}.{ext}"
    return os.path.join(
        "checkout_images", instance.employee.employee_id, today, new_filename
    )


class Employee(models.Model):
    """Employee model with salary info and synced face template"""
    employee_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True, null=True, blank=True)
    department = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    designation = models.CharField(max_length=50, blank=True)
    bank_account = models.CharField(max_length=100, blank=True, null=True)
    branch = models.CharField(max_length=50, blank=True)
    employee_image = models.ImageField(
        upload_to="employee_photos/", null=True, blank=True
    )

    facial_template = models.TextField(
        null=True,
        blank=True,
        help_text="Base64 FaceSDK template provided by the Android app",
    )

    monthly_salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Monthly salary in BDT for bonus/fine calculations",
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Whether employee is currently active in the company"
    )
    date_inactive = models.DateField(
        null=True,
        blank=True,
        help_text="Date when employee was made inactive (left company)"
    )
    hire_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when employee was hired"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        old_employee_id = None
        if self.pk:
            try:
                old_employee = Employee.objects.get(pk=self.pk)
                old_employee_id = old_employee.employee_id
            except Employee.DoesNotExist:
                pass

        if not self.is_active and not self.date_inactive:
            from datetime import date
            self.date_inactive = date.today()
        elif self.is_active and self.date_inactive:
            self.date_inactive = None

        super().save(*args, **kwargs)

        if old_employee_id and old_employee_id != self.employee_id:
            self._rename_image_directories(old_employee_id, self.employee_id)

    def _rename_image_directories(self, old_id, new_id):
        """Rename image directories when employee_id changes"""
        import os
        import shutil
        from django.conf import settings
        
        try:
            media_root = settings.MEDIA_ROOT
            
            # Rename checkin directory
            old_checkin = os.path.join(media_root, 'checkin_images', old_id)
            new_checkin = os.path.join(media_root, 'checkin_images', new_id)
            
            if os.path.exists(old_checkin):
                if os.path.exists(new_checkin):
                    # Merge directories
                    for item in os.listdir(old_checkin):
                        shutil.move(os.path.join(old_checkin, item), os.path.join(new_checkin, item))
                    os.rmdir(old_checkin)
                else:
                    os.rename(old_checkin, new_checkin)
            
            # Rename checkout directory
            old_checkout = os.path.join(media_root, 'checkout_images', old_id)
            new_checkout = os.path.join(media_root, 'checkout_images', new_id)
            
            if os.path.exists(old_checkout):
                if os.path.exists(new_checkout):
                    # Merge directories
                    for item in os.listdir(old_checkout):
                        shutil.move(os.path.join(old_checkout, item), os.path.join(new_checkout, item))
                    os.rmdir(old_checkout)
                else:
                    os.rename(old_checkout, new_checkout)
            
            # Update attendance record image paths
            records = AttendanceRecord.objects.filter(employee=self)
            for record in records:
                updated = False
                if record.checkin_image and old_id in record.checkin_image.name:
                    record.checkin_image.name = record.checkin_image.name.replace(f'checkin_images/{old_id}/', f'checkin_images/{new_id}/')
                    updated = True
                if record.checkout_image and old_id in record.checkout_image.name:
                    record.checkout_image.name = record.checkout_image.name.replace(f'checkout_images/{old_id}/', f'checkout_images/{new_id}/')
                    updated = True
                if updated:
                    record.save()
                    
        except Exception as e:
            # Silently fail to avoid breaking employee saves
            print(f"Directory rename failed: {e}")

    def __str__(self):
        return f"{self.employee_id} - {self.name}"


class SalaryStatistic(models.Model):
    """
    Per-employee monthly salary statistics used for PDF exports.
    """

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    month = models.PositiveIntegerField()
    year = models.PositiveIntegerField()

    basic_salary = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    house_rent = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    medical_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    conveyance_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    food_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    other_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    gross_salary = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    working_days = models.PositiveIntegerField(default=0)
    weekends = models.PositiveIntegerField(default=0)
    leave_days = models.PositiveIntegerField(default=0)
    holidays = models.PositiveIntegerField(default=0)
    attended_days = models.PositiveIntegerField(default=0)

    ot_hours = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))
    ot_rate = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    ot_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    hd_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    attendance_bonus = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    required_attendance_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"), help_text="Minimum attendance percentage required for bonus")
    
    late_fine = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    late_needed = models.PositiveIntegerField(default=0, help_text="Number of late days to trigger one fine unit")
    
    other_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    tds_percent = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))

    stamp = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    payable = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    use_default = models.BooleanField(default=True, help_text="If enabled, values will sync from default template on each export")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("employee", "month", "year")
        ordering = ["employee__name"]

    def __str__(self):
        return f"{self.employee.name} - {self.month}/{self.year}"

    def save(self, *args, **kwargs):
        try:
            self.ot_amount = self.ot_hours * self.ot_rate
            self.gross_salary = (
                self.basic_salary
                + self.house_rent
                + self.medical_allowance
                + self.conveyance_allowance
                + self.food_allowance
                + self.other_allowance
            )
            tds_amount = Decimal("0.00")
            if self.tds_percent:
                total_allowances = (
                    self.house_rent
                    + self.medical_allowance
                    + self.conveyance_allowance
                    + self.food_allowance
                    + self.other_allowance
                    + self.hd_allowance
                    + self.attendance_bonus
                )
                net_allowances = total_allowances - self.late_fine - self.other_deduction
                if net_allowances < 0:
                    net_allowances = Decimal("0.00")
                taxable_others = net_allowances * Decimal("0.6666")
                taxable_income = self.basic_salary + self.ot_amount + taxable_others
                if taxable_income < 0:
                    taxable_income = Decimal("0.00")
                tds_amount = (taxable_income * self.tds_percent) / Decimal("100")
            self.payable = (
                self.gross_salary
                - tds_amount
                - self.stamp
                + self.attendance_bonus
                + self.hd_allowance
                + self.ot_amount
                - self.late_fine
                - self.other_deduction
            )
        except Exception:
            pass
        super().save(*args, **kwargs)


class SalaryStatisticDefault(models.Model):
    """
    Default salary statistic template applied when employee stats do not yet exist.
    """

    house_rent = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    medical_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    conveyance_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    food_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    other_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    ot_rate = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    hd_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    attendance_bonus = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    required_attendance_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"), help_text="Minimum attendance percentage required for bonus")
    
    late_fine = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    late_needed = models.PositiveIntegerField(default=0, help_text="Number of late days to trigger one fine unit")

    tds_percent = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    stamp = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    def __str__(self):
        return "Salary Statistic Defaults"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Apply defaults immediately to all stats that opt-in
        fields_to_copy = [
            "house_rent",
            "medical_allowance",
            "conveyance_allowance",
            "food_allowance",
            "other_allowance",
            "ot_rate",
            "hd_allowance",
            "attendance_bonus",
            "required_attendance_percent",
            "late_fine",
            "late_needed",
            "tds_percent",
            "stamp",
        ]
        updates = {}
        for f in fields_to_copy:
            updates[f] = getattr(self, f)

        # Only update current and future months to protect history
        from django.utils import timezone
        from django.db.models import Q
        now = timezone.now()
        
        target_stats = SalaryStatistic.objects.filter(
            use_default=True
        ).filter(
            Q(year__gt=now.year) | Q(year=now.year, month__gte=now.month)
        )

        for stat in target_stats:
            changed = False
            for f, val in updates.items():
                setattr(stat, f, val)
                changed = True
            if changed:
                stat.ot_amount = stat.ot_hours * stat.ot_rate
                stat.gross_salary = (
                    stat.basic_salary
                    + stat.house_rent
                    + stat.medical_allowance
                    + stat.conveyance_allowance
                    + stat.food_allowance
                    + stat.other_allowance
                )
                tds_amount = Decimal("0.00")
                if stat.tds_percent:
                    total_allowances = (
                        stat.house_rent
                        + stat.medical_allowance
                        + stat.conveyance_allowance
                        + stat.food_allowance
                        + stat.other_allowance
                        + stat.hd_allowance
                        + stat.attendance_bonus
                    )
                    net_allowances = total_allowances - stat.late_fine - stat.other_deduction
                    if net_allowances < 0:
                        net_allowances = Decimal("0.00")
                    taxable_others = net_allowances * Decimal("0.6666")
                    taxable_income = stat.basic_salary + stat.ot_amount + taxable_others
                    if taxable_income < 0:
                        taxable_income = Decimal("0.00")
                    tds_amount = (taxable_income * stat.tds_percent) / Decimal("100")
                stat.payable = (
                    stat.gross_salary
                    - tds_amount
                    + stat.attendance_bonus
                    + stat.hd_allowance
                    + stat.ot_amount
                    - stat.late_fine
                    - stat.other_deduction
                )
                stat.save()

    def delete(self, *args, **kwargs):
        # When deleting defaults, clear dependent fields for use_default stats
        fields_to_reset = [
            "house_rent",
            "medical_allowance",
            "conveyance_allowance",
            "food_allowance",
            "other_allowance",
            "ot_rate",
            "hd_allowance",
            "attendance_bonus",
            "required_attendance_percent",
            "tds_percent",
            "tds_amount",
            "stamp",
            "late_fine",
            "late_needed",
        ]
        for stat in SalaryStatistic.objects.filter(use_default=True):
            changed = False
            for f in fields_to_reset:
                val = getattr(stat, f)
                zero_val = Decimal("0.00") if isinstance(val, Decimal) else 0
                if val != zero_val:
                    setattr(stat, f, zero_val)
                    changed = True
            if changed:
                stat.gross_salary = (
                    stat.basic_salary
                    + stat.house_rent
                    + stat.medical_allowance
                    + stat.conveyance_allowance
                    + stat.food_allowance
                    + stat.other_allowance
                )
                stat.payable = stat.gross_salary - stat.stamp + stat.attendance_bonus + stat.hd_allowance + stat.ot_amount
                stat.save()
        super().delete(*args, **kwargs)


# Keep SalaryStatistic basic salary in sync when Employee monthly_salary changes
@receiver(post_save, sender=Employee)
def sync_salary_stat_basic(sender, instance, **kwargs):
    try:
        stats = SalaryStatistic.objects.filter(employee=instance)
        updated = []
        for stat in stats:
            if stat.use_default or stat.basic_salary == 0:
                stat.basic_salary = instance.monthly_salary
                stat.ot_amount = stat.ot_hours * stat.ot_rate
                stat.gross_salary = (
                    stat.basic_salary
                    + stat.house_rent
                    + stat.medical_allowance
                    + stat.conveyance_allowance
                    + stat.food_allowance
                    + stat.other_allowance
                )
                if stat.tds_percent and (stat.tds_amount == 0 or stat.use_default):
                    total_allowances = (
                        stat.house_rent
                        + stat.medical_allowance
                        + stat.conveyance_allowance
                        + stat.food_allowance
                        + stat.other_allowance
                        + stat.hd_allowance
                        + stat.attendance_bonus
                    )
                    net_allowances = total_allowances - stat.late_fine - stat.other_deduction
                    if net_allowances < 0:
                        net_allowances = Decimal("0.00")
                    taxable_others = net_allowances * Decimal("0.6666")
                    taxable_income = stat.basic_salary + stat.ot_amount + taxable_others
                    if taxable_income < 0:
                        taxable_income = Decimal("0.00")
                    stat.tds_amount = (taxable_income * stat.tds_percent) / Decimal("100")
                stat.payable = (
                    stat.gross_salary
                    - stat.tds_amount
                    + stat.attendance_bonus
                    + stat.hd_allowance
                    + stat.ot_amount
                )
                updated.append(stat)
        if updated:
            SalaryStatistic.objects.bulk_update(
                updated,
                [
                    "basic_salary",
                    "ot_amount",
                    "gross_salary",
                    "tds_amount",
                    "payable",
                    "updated_at",
                ],
            )
    except Exception:
        # Fail silently to avoid blocking employee saves
        pass
class Shift(models.Model):
    """
    Work shift configuration with timing and thresholds.
    
    Features:
    - Only one shift can be active at a time
    - Configurable work hours and late tolerance
    - Used for attendance status calculations
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
    late_override_minutes = models.PositiveIntegerField(
        default=0,
        help_text="If late beyond this many minutes, override status using late_override_status",
    )
    late_override_status = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        choices=[
            ("Late", "Late"),
            ("Absent", "Absent"),
            ("Early Leave", "Early Leave"),
            ("Half Day", "Half Day"),
            ("Present", "Present"),
            ("Pending", "Pending"),
        ],
        help_text="Status to apply when late beyond late_override_minutes (optional)",
    )
    is_active = models.BooleanField(
        default=False, help_text="Only one shift should be active at a time"
    )

    class Meta:
        ordering = ("-is_active", "name")

    def __str__(self):
        return f"{self.name} {'(active)' if self.is_active else ''}"

    def save(self, *args, **kwargs):
        """Ensure only one shift is active at a time using atomic transaction"""
        if self.is_active:
            from django.db import transaction

            with transaction.atomic():
                # Deactivate all other shifts before activating this one
                self.__class__.objects.filter(is_active=True).exclude(
                    pk=self.pk
                ).update(is_active=False)
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)


def get_active_shift():
    """Get the currently active shift configuration"""
    return Shift.objects.filter(is_active=True).first()


class AttendanceRecord(models.Model):
    """
    Core attendance record with automatic status calculation.
    
    Key Features:
    - Timezone-aware checkin/checkout times
    - Automatic status calculation (Present/Absent/Half Day/etc.)
    - Late duration tracking with precision
    - Image storage for verification
    - Shift snapshot preservation for historical accuracy
    - Automatic salary adjustment triggers
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
            ("Late", "Late"),
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

    is_status_override = models.BooleanField(
        default=False,
        help_text="If True, status is manually set and will not be auto-calculated."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-date", "-checkin_time")
    
    def delete(self, *args, **kwargs):
        """
        Custom delete to remove associated images when attendance record is deleted.
        
        Process:
        1. Delete checkin image file if exists
        2. Delete checkout image file if exists
        3. Delete the attendance record
        """
        import os
        
        # Delete checkin image
        if self.checkin_image:
            try:
                if os.path.exists(self.checkin_image.path):
                    os.remove(self.checkin_image.path)
            except:
                pass
        
        # Delete checkout image
        if self.checkout_image:
            try:
                if os.path.exists(self.checkout_image.path):
                    os.remove(self.checkout_image.path)
            except:
                pass
        
        super().delete(*args, **kwargs)

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
        Calculate precise late duration with timezone awareness.
        
        Algorithm:
        1. Convert checkin time to Dhaka timezone
        2. Build shift start datetime for same date
        3. Add allowed late minutes buffer
        4. Calculate difference if checkin > allowed end time
        
        Returns:
        - None: No checkin time or shift data
        - timedelta(0): On time (within allowed window)
        - timedelta(positive): Late duration in seconds
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
        Intelligent status calculation based on work hours, not lateness.
        
        Status Priority (work hours over lateness):
        1. Absent: No checkin AND no checkout
        2. Pending: Missing either checkin OR checkout
        3. Present: Worked >= 8 hours (configurable)
        4. Half Day: Worked >= 4 hours but < 8 hours
        5. Early Leave: Worked < 4 hours
        
        Note: Late tracking is separate from status for better UX
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
            base_status = "Present"
        elif shift and worked_hours >= float(shift.half_day_hours):
            base_status = "Half Day"
        else:
            base_status = "Early Leave"

        # Optional late override: if late beyond configured minutes, apply configured status
        try:
            if (
                shift
                and shift.late_override_status
                and shift.late_override_minutes is not None
                and late_dur
                and late_dur.total_seconds() > shift.late_override_minutes * 60
            ):
                return shift.late_override_status
        except Exception:
            pass

        return base_status

    def save(self, *args, **kwargs):
        """
        Smart save with automatic calculations and salary updates.
        
        Process:
        1. Snapshot current active shift for new records
        2. Preserve manual statuses (On Leave, Holiday, Off Day)
        3. Auto-calculate status and late duration
        4. Trigger real-time salary recalculation
        5. Update related salary adjustments automatically
        """
        # If new record and no explicit shift, snapshot the current active shift
        if self.pk is None and self.shift is None:
            try:
                self.shift = get_active_shift()
            except Exception:
                self.shift = None

        manual_statuses = ["On Leave", "Holiday", "Off Day"]
        # Skip auto-calculation if override is active or status is one of the manual types
        if not self.is_status_override and self.status not in manual_statuses:
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
        

    







class BulkHoliday(models.Model):
    """
    Advanced holiday management with scope-based targeting.
    
    Capabilities:
    - Mass holiday creation for multiple employees
    - Scope filtering: All, Department, Designation, Custom
    - Government holiday auto-generation
    - Smart processing (doesn't override existing attendance)
    - Automatic attendance record creation/deletion
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
        """
        Intelligent holiday processing with overtime protection.
        
        Process:
        1. Get employees based on scope (all/department/designation/custom)
        2. Iterate through date range
        3. Create holiday records only if no existing attendance
        4. Preserve existing records (allows overtime work on holidays)
        
        Returns: Number of holiday records created
        """
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
        """
        Auto-process holidays on save with activation control.
        
        Behavior:
        - Active holidays: Create attendance records automatically
        - Inactive holidays: Remove existing holiday records
        - Real-time processing for immediate effect
        """
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
        """
        Clean deletion with attendance record cleanup.
        
        Process:
        1. Remove all holiday attendance records for affected dates
        2. Only removes records with 'Holiday' status
        3. Preserves other attendance types (Present, Absent, etc.)
        4. Then delete the holiday configuration
        """
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





# Admin navigation stub models (non-managed, no database tables)
class DeviceRegistration(models.Model):
    token = models.CharField(max_length=255, unique=True)
    platform = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.token


class IntegrationSetting(models.Model):
    """Stores integration credentials (e.g., FCM server key) editable via admin."""
    fcm_server_key = models.TextField(
        blank=True,
        help_text="Paste your Firebase Cloud Messaging server key here."
    )
    fcm_service_account_json = models.TextField(
        blank=True,
        help_text="Optional: paste Firebase service account JSON (used for HTTP v1)."
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Integration Settings"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class DashboardStub(models.Model):
    """Stub model for attendance dashboard admin navigation"""
    class Meta:
        managed = False
        verbose_name = "Attendance Dashboard"
        verbose_name_plural = "Attendance Dashboard"


class SalaryReportStub(models.Model):
    """Stub model for salary report admin navigation"""
    class Meta:
        managed = False
        verbose_name = "Salary Report"
        verbose_name_plural = "Salary Report"


class HolidayManagementStub(models.Model):
    """Stub model for holiday management admin navigation"""
    class Meta:
        managed = False
        verbose_name = "Holiday Management"
        verbose_name_plural = "Holiday Management"


















class CompanyInfo(models.Model):
    """
    Singleton model to store company details for reports.
    """
    name = models.CharField(max_length=255, default="My Company")
    logo = models.ImageField(upload_to="company_logo/", blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    tin = models.CharField("TIN", max_length=100, blank=True, null=True)
    bin = models.CharField("BIN / BFN", max_length=100, blank=True, null=True)
    founder = models.CharField(max_length=255, blank=True, null=True)
    
    class Meta:
        verbose_name = "Company Information"
        verbose_name_plural = "Company Information"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.pk and CompanyInfo.objects.exists():
            # If trying to create a new instance but one exists, update the existing one
            existing = CompanyInfo.objects.first()
            existing.name = self.name
            existing.logo = self.logo
            existing.address = self.address
            existing.email = self.email
            existing.phone = self.phone
            existing.website = self.website
            return existing.save()
        return super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj


class ModeratorLabel(models.Model):
    key = models.CharField(max_length=128, unique=True)
    label = models.CharField(max_length=255, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["key"]

    def __str__(self):
        return f"{self.key}: {self.label or ''}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        from .utils import moderator_labels

        moderator_labels.clear_label_cache()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        from .utils import moderator_labels

        moderator_labels.clear_label_cache()
