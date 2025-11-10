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

    def compute_status(self):
        """
        Computes status using THIS record's effective shift and populates self.late_duration.

        Rules:
          - Absent if no checkin and no checkout
          - Pending if missing one timestamp (but may be Late if checkin exists and beyond allowed window)
          - When both exist, compute worked_hours:
              * Present if worked_hours >= present_hours
              * Half Day if worked_hours >= half_day_hours
              * Otherwise Early Leave unless late rules apply
          - Late is applied when enable_late_status is True and effective late > 0
          Present has precedence over Late when worked_hours >= present_hours
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
            if (
                self.checkin_time
                and shift
                and shift.enable_late_status
                and self._is_late(shift)
            ):
                # compute_status returns Late string, but status choices do not include Late for manual selection;
                # we persist "Late" as computed status (not offered in admin dropdown)
                return "Late"
            return "Pending"

        # both timestamps exist
        worked_hours = (self.checkout_time - self.checkin_time).total_seconds() / 3600.0

        if shift and worked_hours >= float(shift.present_hours):
            return "Present"

        if shift and worked_hours >= float(shift.half_day_hours):
            if shift.enable_late_status and self._is_late(shift):
                return "Late"
            return "Half Day"

        if shift and shift.enable_late_status and self._is_late(shift):
            return "Late"

        return "Early Leave"

    def save(self, *args, **kwargs):
        """
        - On first save (new record) if no shift is set, freeze in the current active shift.
        - Preserve manual statuses: On Leave, Holiday, Off Day.
        - Otherwise recompute status + late_duration based on the record's effective shift.
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


# keep DashboardStub so admin dashboard entry works (non-managed)
class DashboardStub(models.Model):
    class Meta:
        managed = False
        verbose_name = "Attendance Dashboard"
        verbose_name_plural = "Attendance Dashboard"
