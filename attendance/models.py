# Core Django and Python imports
import os
from datetime import datetime, date, timedelta
from decimal import Decimal

# Django framework imports
from django.conf import settings
from django.db import models
from django.utils import timezone
import pytz
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

# Timezone configuration for Bangladesh
dhaka = pytz.timezone("Asia/Dhaka")

# Live feed configuration
LIVEFEED_MAX_PER_DAY = 6
LIVEFEED_CAPTURE_INTERVAL_SECONDS = 3.0
LIVEFEED_RETENTION_DAYS = 3


def dhaka_now():
    """Get current datetime in Dhaka timezone"""
    return timezone.now().astimezone(dhaka)


def employee_checkin_path(instance, filename):
    """Generate organized file path for checkin images with employee name"""
    now = dhaka_now()
    today = now.strftime("%Y-%m-%d")
    timestamp = now.strftime("%H%M%S")
    ext = filename.split(".")[-1]
    # Sanitize employee name for filename (replace spaces, limit length)
    emp_name = instance.employee.name if instance.employee else "unknown"
    safe_name = emp_name.replace(" ", "_").replace("/", "-")[:20]
    new_filename = f"in_{safe_name}_{today}_{timestamp}.{ext}"
    return os.path.join(
        "checkin_images", instance.employee.employee_id, today, new_filename
    )


def employee_checkout_path(instance, filename):
    """Generate organized file path for checkout images with employee name"""
    now = dhaka_now()
    today = now.strftime("%Y-%m-%d")
    timestamp = now.strftime("%H%M%S")
    ext = filename.split(".")[-1]
    # Sanitize employee name for filename (replace spaces, limit length)
    emp_name = instance.employee.name if instance.employee else "unknown"
    safe_name = emp_name.replace(" ", "_").replace("/", "-")[:20]
    new_filename = f"out_{safe_name}_{today}_{timestamp}.{ext}"
    return os.path.join(
        "checkout_images", instance.employee.employee_id, today, new_filename
    )


def livefeed_image_path(instance, filename):
    """Generate organized file path for live feed images"""
    now = dhaka_now()
    today = now.strftime("%Y-%m-%d")
    timestamp = now.strftime("%H%M%S%f")
    ext = filename.split(".")[-1] if "." in filename else "jpg"
    new_filename = f"live_{today}_{timestamp}.{ext}"
    subject_id = "unknown"
    try:
        if getattr(instance, "employee", None) and instance.employee.employee_id:
            subject_id = instance.employee.employee_id
        elif getattr(instance, "subject_identifier", ""):
            subject_id = instance.subject_identifier
    except Exception:
        pass
    subject_id = str(subject_id or "unknown").replace("/", "_")
    return os.path.join("livefeed_images", subject_id, today, new_filename)


def organization_logo_path(instance, filename):
    """Generate organized file path for organization logos"""
    ext = filename.split(".")[-1] if "." in filename else "png"
    return os.path.join("org_logos", instance.slug, f"logo.{ext}")


# =============================================================================
# MULTI-TENANT MODELS
# =============================================================================

class Organization(models.Model):
    """
    Represents a company/organization in the multi-tenant SaaS system.
    Each organization has its own employees, attendance records, and settings.
    Also holds company details for PDFs/reports (merged from CompanyInfo).
    """
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, help_text="URL-friendly identifier, e.g., 'company-abc'")
    
    # Contact Information
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    logo = models.ImageField(upload_to=organization_logo_path, blank=True, null=True)
    website = models.URLField(blank=True, null=True, help_text="Company website URL")
    
    # Business Registration (for PDFs/reports)
    tin = models.CharField("TIN", max_length=100, blank=True, null=True, help_text="Tax Identification Number")
    bin = models.CharField("BIN / BFN", max_length=100, blank=True, null=True, help_text="Business Identification Number")
    founder = models.CharField(max_length=255, blank=True, null=True, help_text="Founder/Owner name for reports")
    
    # Status & Limits
    is_active = models.BooleanField(default=True, help_text="Whether this organization is active")
    max_employees = models.PositiveIntegerField(default=100, help_text="Maximum employees allowed (license limit)")
    max_devices = models.PositiveIntegerField(default=5, help_text="Maximum devices allowed")
    
    # Subscription Plan (optional - overrides can be set via max_employees/max_devices directly)
    plan = models.ForeignKey(
        'SubscriptionPlan',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='organizations',
        help_text="Subscription plan for this organization (overrides default limits)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"

    def __str__(self):
        return self.name

    def employee_count(self):
        """Get current number of employees in this organization"""
        return self.employees.filter(is_active=True).count()

    def device_count(self):
        """Get current number of active devices"""
        return self.devices.filter(is_active=True).count()

    def is_at_employee_limit(self):
        """Check if organization has reached employee limit"""
        return self.employee_count() >= self.max_employees

    def is_at_device_limit(self):
        """Check if organization has reached device limit"""
        return self.device_count() >= self.max_devices


class Device(models.Model):
    """
    Represents a physical device (tablet/phone) running the face recognition APK.
    The device_id is what the APK sends in API requests to identify the organization.
    """
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='devices',
        help_text="Organization this device belongs to"
    )
    
    device_id = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Unique identifier sent by APK (configured in app settings)"
    )
    device_name = models.CharField(
        max_length=255,
        help_text="Human-readable name, e.g., 'Main Gate Tablet'"
    )
    location = models.CharField(
        max_length=255,
        blank=True,
        help_text="Physical location, e.g., 'Main Entrance'"
    )
    
    is_active = models.BooleanField(default=True)
    last_seen = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Last time this device made an API call"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['organization', 'device_name']
        verbose_name = "Device"
        verbose_name_plural = "Devices"

    def __str__(self):
        return f"{self.device_name} ({self.organization.name})"

    def update_last_seen(self):
        """Update last_seen timestamp (called on API requests)"""
        self.last_seen = timezone.now()
        self.save(update_fields=['last_seen'])


class OrganizationUser(models.Model):
    """
    Links Django users to organizations with specific roles.
    Super admins have organization=None and can access all organizations.
    org_main_admin is the primary admin for an org and can create other admins.
    """
    ROLE_CHOICES = [
        ('super_admin', 'Super Admin'),           # Full access to all orgs
        ('org_main_admin', 'Organization Main Admin'),  # Primary org admin, can create others
        ('org_admin', 'Organization Admin'),      # Can manage their org
        ('org_viewer', 'Organization Viewer'),    # View-only access
    ]

    user = models.OneToOneField(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='org_profile'
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='users',
        help_text="Organization this user belongs to. Null for super admins."
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='org_viewer'
    )
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_org_users',
        help_text="User who created this org user"
    )

    class Meta:
        verbose_name = "Organization User"
        verbose_name_plural = "Organization Users"

    def __str__(self):
        org_name = self.organization.name if self.organization else "All Organizations"
        return f"{self.user.username} - {self.get_role_display()} ({org_name})"

    def is_super_admin(self):
        """Check if user is super admin"""
        return self.role == 'super_admin'

    def can_access_organization(self, org):
        """Check if user can access a specific organization"""
        if self.is_super_admin():
            return True
        return self.organization == org


class OrganizationSettings(models.Model):
    """
    Per-organization configuration settings.
    Each organization can have its own timezone, thresholds, and preferences.
    """
    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name='settings'
    )

    # Time & Attendance
    timezone = models.CharField(max_length=50, default='Asia/Dhaka')
    work_week_start = models.PositiveIntegerField(
        default=0,
        help_text="0=Sunday, 1=Monday, etc."
    )
    
    # Face Recognition Settings
    liveness_threshold = models.FloatField(default=0.7)
    match_threshold = models.FloatField(default=0.8)
    
    # Voice Settings
    default_voice_language = models.CharField(max_length=10, default='en')
    voice_enabled = models.BooleanField(default=True)
    
    # Notifications
    email_on_late = models.BooleanField(default=False)
    email_on_absent = models.BooleanField(default=False)
    admin_email = models.EmailField(blank=True, null=True)

    class Meta:
        verbose_name = "Organization Settings"
        verbose_name_plural = "Organization Settings"

    def __str__(self):
        return f"Settings for {self.organization.name}"


# =============================================================================
# MAIN MODELS
# =============================================================================

class Employee(models.Model):
    """Employee model with salary info and synced face template"""
    # Multi-tenant: Organization link
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='employees',
        null=True,  # Temporarily nullable for migration
        blank=True,
        help_text="Organization this employee belongs to"
    )
    
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

            # Rename livefeed directory
            old_livefeed = os.path.join(media_root, 'livefeed_images', old_id)
            new_livefeed = os.path.join(media_root, 'livefeed_images', new_id)

            if os.path.exists(old_livefeed):
                if os.path.exists(new_livefeed):
                    for item in os.listdir(old_livefeed):
                        shutil.move(os.path.join(old_livefeed, item), os.path.join(new_livefeed, item))
                    os.rmdir(old_livefeed)
                else:
                    os.rename(old_livefeed, new_livefeed)
            
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

            # Update live feed image paths
            try:
                live_images = LiveFeedImage.objects.filter(employee=self)
                for image in live_images:
                    if image.image and old_id in image.image.name:
                        image.image.name = image.image.name.replace(
                            f'livefeed_images/{old_id}/', f'livefeed_images/{new_id}/'
                        )
                    if image.subject_identifier == old_id:
                        image.subject_identifier = new_id
                    image.save()
            except Exception:
                pass
                    
        except Exception as e:
            # Silently fail to avoid breaking employee saves
            print(f"Directory rename failed: {e}")

    def __str__(self):
        return f"{self.employee_id} - {self.name}"


# Signal to clean up employee images when employee is deleted
@receiver(pre_delete, sender=Employee)
def cleanup_employee_images(sender, instance, **kwargs):
    """
    Delete all images associated with an employee when the employee is deleted.
    This includes:
    - Check-in images
    - Check-out images
    - Live feed images
    - Employee photo
    """
    import shutil
    
    try:
        media_root = settings.MEDIA_ROOT
        employee_id = instance.employee_id
        
        # Delete employee photo if exists
        if instance.employee_image:
            try:
                if os.path.isfile(instance.employee_image.path):
                    os.remove(instance.employee_image.path)
            except Exception:
                pass
        
        # Delete checkin images folder
        checkin_dir = os.path.join(media_root, 'checkin_images', employee_id)
        if os.path.exists(checkin_dir):
            shutil.rmtree(checkin_dir, ignore_errors=True)
        
        # Delete checkout images folder
        checkout_dir = os.path.join(media_root, 'checkout_images', employee_id)
        if os.path.exists(checkout_dir):
            shutil.rmtree(checkout_dir, ignore_errors=True)
        
        # Delete livefeed images folder
        livefeed_dir = os.path.join(media_root, 'livefeed_images', employee_id)
        if os.path.exists(livefeed_dir):
            shutil.rmtree(livefeed_dir, ignore_errors=True)
        
        print(f"Cleaned up images for employee: {employee_id}")
        
    except Exception as e:
        # Log but don't prevent deletion
        print(f"Image cleanup failed for employee {instance.employee_id}: {e}")

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

    organization = models.ForeignKey(
        "Organization", on_delete=models.CASCADE, null=True, blank=True, related_name="shifts"
    )
    name = models.CharField(max_length=80)
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
        unique_together = ("organization", "name")

    def __str__(self):
        return f"{self.name} {'(active)' if self.is_active else ''}"

    def save(self, *args, **kwargs):
        """Ensure only one shift is active at a time using atomic transaction"""
        if self.is_active:
            from django.db import transaction

            with transaction.atomic():
                # Deactivate all other shifts within the SAME organization before activating this one
                qs = self.__class__.objects.filter(is_active=True).exclude(pk=self.pk)
                
                if self.organization:
                    qs = qs.filter(organization=self.organization)
                else:
                    # Global shift being activated? Should we deactivate other globals?
                    # Or maybe all shifts? For safety, let's say globals compete with globals.
                    qs = qs.filter(organization__isnull=True)
                
                qs.update(is_active=False)
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)


def get_active_shift(organization=None):
    """
    Get the currently active shift configuration.
    Priority:
    1. Active shift for the specific organization.
    2. Active global shift (organization=None).
    """
    if organization:
        # Try to find specific org shift
        if isinstance(organization, (int, str)) and str(organization).isdigit():
            shift = Shift.objects.filter(organization_id=organization, is_active=True).first()
        else:
            shift = Shift.objects.filter(organization=organization, is_active=True).first()
            
        if shift:
            return shift
            
    # Fallback to global active shift
    return Shift.objects.filter(organization__isnull=True, is_active=True).first()


class LiveFeedImage(models.Model):
    """Short-retention live snapshots streamed from devices."""
    
    # Multi-tenant: Organization link
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='livefeed_images',
        null=True,
        blank=True,
        help_text="Organization this image belongs to"
    )

    employee = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employee_livefeed_images",
    )
    subject_identifier = models.CharField(
        max_length=100,
        db_index=True,
        default="unknown",
        help_text="Employee ID used for quota; 'unknown' when not matched",
    )
    image = models.ImageField(upload_to=livefeed_image_path)
    device_id = models.CharField(max_length=100, null=True, blank=True)
    captured_at = models.DateTimeField(default=dhaka_now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-captured_at", "-id")
        indexes = [
            models.Index(fields=["captured_at"]),
            models.Index(fields=["employee", "captured_at"]),
            models.Index(fields=["subject_identifier", "captured_at"]),
        ]

    def __str__(self):
        subject = self.subject_identifier or "unknown"
        return f"{subject} @ {self.captured_at}"

    def delete(self, *args, **kwargs):
        """Remove image file from disk when deleting records."""
        image_path = None
        if self.image:
            try:
                image_path = self.image.path
            except Exception:
                image_path = None

        super().delete(*args, **kwargs)

        if image_path:
            try:
                if os.path.exists(image_path):
                    os.remove(image_path)
            except Exception:
                pass

    @classmethod
    def purge_older_than(cls, days=LIVEFEED_RETENTION_DAYS):
        """Delete records (and files) older than the retention window."""
        cutoff = dhaka_now() - timedelta(days=days)
        removed = 0
        for item in cls.objects.filter(captured_at__lt=cutoff):
            item.delete()
            removed += 1
        return removed


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
    
    # Multi-tenant: Organization link
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='attendance_records',
        null=True,
        blank=True,
        help_text="Organization this record belongs to"
    )

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
        return self.shift or get_active_shift(self.employee.organization if self.employee else None)

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
                self.shift = get_active_shift(self.employee.organization if self.employee else None)
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
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE, null=True, blank=True, related_name='holidays')
    
    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Holiday'
        verbose_name_plural = 'Holidays'
    
    def __str__(self):
        return f"{self.name} ({self.start_date} to {self.end_date})"
    
    def get_affected_employees(self):
        """Get list of employees affected by this holiday"""
        qs = Employee.objects.all()
        if self.organization:
            qs = qs.filter(organization=self.organization)

        if self.scope == 'all':
            return qs
        elif self.scope == 'department':
            return qs.filter(department=self.department)
        elif self.scope == 'designation':
            return qs.filter(designation=self.designation)
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


class VoiceSetting(models.Model):
    """Configurable TTS/voice settings exposed to the Android app."""

    NAME_FORMAT_CHOICES = [
        ("full", "Full Name"),
        ("first", "First Name"),
        ("last", "Last Name"),
        ("custom", "Custom Template"),
    ]
    VOICE_MODE_CHOICES = [
        ("default", "Default"),
        ("calm", "Calm"),
        ("energetic", "Energetic"),
        ("slow", "Slow"),
        ("soft", "Soft"),
        ("clear_slow", "Clear & Slow"),
        ("female_soft", "Female Soft"),
        ("female_clear", "Female Clear"),
    ]

    default_language = models.CharField(
        max_length=16,
        default="en-US",
        help_text="Primary TTS locale (e.g., en-US, bn-BD, hi-IN, zh-CN, ko-KR, ja-JP).",
    )
    additional_languages = models.JSONField(
        default=list,
        blank=True,
        help_text="List of fallback locales in priority order.",
    )
    name_format = models.CharField(
        max_length=12,
        choices=NAME_FORMAT_CHOICES,
        default="full",
        help_text="How names should be spoken in voice prompts.",
    )
    custom_name_template = models.CharField(
        max_length=64,
        blank=True,
        help_text="Use {first}, {last}, {full} placeholders when name_format is custom.",
    )
    speech_rate = models.FloatField(
        default=1.0, help_text="TTS speech rate (1.0 = normal)."
    )
    pitch = models.FloatField(default=1.0, help_text="TTS pitch (1.0 = normal).")
    voice_mode = models.CharField(
        max_length=16,
        choices=VOICE_MODE_CHOICES,
        default="default",
        help_text="Optional mode hint for the client.",
    )
    voice_repeat_delay_seconds = models.FloatField(
        default=1.5,
        help_text="Delay in seconds between repeated voice prompts.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Voice Setting"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class TextMessageSetting(models.Model):
    """Configurable check-in/out text display timing and templates."""

    checkin_text = models.CharField(max_length=255, default="Welcome {name}")
    checkout_text = models.CharField(max_length=255, default="Goodbye {name}")
    checkin_interval_seconds = models.FloatField(default=3.0)
    checkout_interval_seconds = models.FloatField(default=3.0)
    checkin_active = models.BooleanField(default=True)
    checkout_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Text Message Setting"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class ContextSetting(models.Model):
    """Switches for text/voice context display."""

    text_message_display = models.BooleanField(default=True)
    voice_message_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Context Setting"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class MessageSetting(models.Model):
    """(Deprecated) Wrapper for voice/text/context. Kept for migration history."""
    class Meta:
        managed = False


class VoiceNameOverride(models.Model):
    """Per-employee per-language spoken name."""

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="voice_names")
    language_code = models.CharField(max_length=16, default="en-US")
    spoken_name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("employee", "language_code")
        ordering = ("employee__employee_id", "language_code")

    def __str__(self):
        return f"{self.employee.employee_id} ({self.language_code}) -> {self.spoken_name}"


class EmployeeVoicePreference(models.Model):
    """Per-employee preferred language for voice output."""

    employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name="voice_preference")
    language_code = models.CharField(max_length=16, default="en-US")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.employee.employee_id} -> {self.language_code}"


class VoicePhraseOverride(models.Model):
    """Per-language voice phrases for checkin/checkout."""

    language_code = models.CharField(max_length=16, default="en-US")
    checkin_phrase = models.CharField(
        max_length=255,
        default="Welcome {name}",
        help_text="Use {name} placeholder",
    )
    checkout_phrase = models.CharField(
        max_length=255,
        default="Goodbye {name}",
        help_text="Use {name} placeholder",
    )
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("language_code",)
        ordering = ("language_code",)

    def __str__(self):
        return f"Phrases {self.language_code}"


class LiveFeedStub(models.Model):
    """Stub model used to expose the Live Feed page inside Django admin."""

    class Meta:
        managed = False
        verbose_name = "Live Feed"
        verbose_name_plural = "Live Feed"


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


# ============================================================================
# SaaS MODELS: Subscription Plans and Audit Logs
# ============================================================================

class SubscriptionPlan(models.Model):
    """
    Subscription plans with different limits and features.
    Organizations are linked to plans for billing and feature access.
    """
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    max_employees = models.IntegerField(default=10)
    max_devices = models.IntegerField(default=2)
    features = models.JSONField(default=list, help_text='List of enabled features')
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price_yearly = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False, help_text='Default plan for new organizations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['price_monthly']

    def __str__(self):
        return f"{self.name} (Max: {self.max_employees} employees)"


class AuditLog(models.Model):
    """
    Audit log for tracking user actions across the system.
    Super admins see all logs, org admins see only their org's logs.
    """
    ACTION_CHOICES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('view', 'View'),
        ('export', 'Export'),
        ('import', 'Import'),
    ]

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='audit_logs',
        null=True,
        blank=True,
    )
    user_email = models.CharField(max_length=200)
    user_name = models.CharField(max_length=200, blank=True)
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    resource_type = models.CharField(max_length=50)
    resource_id = models.IntegerField(null=True, blank=True)
    resource_name = models.CharField(max_length=200, blank=True)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user_email} {self.action} {self.resource_type} @ {self.timestamp}"

    @classmethod
    def log_action(cls, request=None, organization_id=None, user_email=None, user_name=None,
                   action='view', resource_type='unknown', resource_id=None, resource_name='', details=None):
        """
        Helper method to create an audit log entry.
        
        Usage:
            AuditLog.log_action(
                request=request,
                organization_id=1,
                user_email='user@example.com',
                action='create',
                resource_type='employee',
                resource_id=123,
                resource_name='John Doe',
                details={'field': 'value'}
            )
        """
        ip_address = None
        user_agent = ''
        
        if request:
            # Extract IP from request
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0].strip()
            else:
                ip_address = request.META.get('REMOTE_ADDR')
            user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        return cls.objects.create(
            organization_id=organization_id,
            user_email=user_email or '',
            user_name=user_name or '',
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name or '',
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
