from django.contrib import admin
from django import forms
from django.utils.html import format_html
from django.forms.widgets import SplitDateTimeWidget
from .models import Employee, AttendanceRecord, DashboardStub, Shift, SalaryAdjustment, SalaryReportStub
import pytz

dhaka = pytz.timezone("Asia/Dhaka")

admin.site.site_header = "BaraBDOnline.XYZ"
admin.site.site_title = "barabdonline.xyz"
admin.site.index_title = "Welcome to barabdonline.xyz attendance Dashboard"


class AttendanceRecordForm(forms.ModelForm):
    class Meta:
        model = AttendanceRecord
        fields = "__all__"
        widgets = {
            "checkin_time": SplitDateTimeWidget(
                date_attrs={"type": "date"}, time_attrs={"type": "time"}
            ),
            "checkout_time": SplitDateTimeWidget(
                date_attrs={"type": "date"}, time_attrs={"type": "time"}
            ),
        }


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    form = AttendanceRecordForm
    list_display = (
        "employee",
        "date",
        "formatted_checkin_time",
        "formatted_checkout_time",
        "status",
        "formatted_late_duration",
        "device_id",  # NEW
        "checkin_image_preview",
        "checkout_image_preview",
    )
    list_filter = ("date", "status", "employee__department")
    search_fields = ("employee__employee_id", "employee__name", "device_id")
    readonly_fields = ("late_duration",)

    def formatted_checkin_time(self, obj):
        if obj.checkin_time:
            return obj.checkin_time.astimezone(dhaka).strftime("%I:%M %p")
        return "—"

    formatted_checkin_time.short_description = "Check-In Time"

    def formatted_checkout_time(self, obj):
        if obj.checkout_time:
            return obj.checkout_time.astimezone(dhaka).strftime("%I:%M %p")
        return "—"

    formatted_checkout_time.short_description = "Check-Out Time"

    def formatted_late_duration(self, obj):
        if obj.late_duration:
            total = int(obj.late_duration.total_seconds())
            hours, rem = divmod(total, 3600)
            minutes, seconds = divmod(rem, 60)
            if hours:
                return f"{hours:d}:{minutes:02d}:{seconds:02d}"
            return f"{minutes:d}:{seconds:02d}"
        return "—"

    formatted_late_duration.short_description = "Late (m:s)"

    def checkin_image_preview(self, obj):
        if obj.checkin_image:
            return format_html(
                '<img src="{}" width="60" height="60" style="object-fit:cover;border-radius:5px;" />',
                obj.checkin_image.url,
            )
        return "—"

    checkin_image_preview.short_description = "Check-In Image"

    def checkout_image_preview(self, obj):
        if obj.checkout_image:
            return format_html(
                '<img src="{}" width="60" height="60" style="object-fit:cover;border-radius:5px;" />',
                obj.checkout_image.url,
            )
        return "—"

    checkout_image_preview.short_description = "Check-Out Image"


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = (
        "employee_image_tag",
        "employee_id",
        "name",
        "department",
        "designation",
        "branch",
        "email",
    )
    search_fields = ("employee_id", "name", "department")
    list_display_links = ("employee_id",)

    def employee_image_tag(self, obj):
        if obj.employee_image and hasattr(obj.employee_image, "url"):
            url = obj.employee_image.url
        else:
            url = "/static/icons/default-avatar.png"
        return format_html(
            '<img src="{}" style="width:40px;height:40px;object-fit:cover;border-radius:50%;border:1px solid #ddd;" alt="{}" />',
            url,
            obj.name,
        )

    employee_image_tag.short_description = ""


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "shift_start",
        "shift_end",
        "present_hours",
        "half_day_hours",
        "allowed_late_minutes",
        "enable_late_status",
        "is_active",
    )
    list_editable = ("is_active",)
    search_fields = ("name",)


@admin.register(SalaryAdjustment)
class SalaryAdjustmentAdmin(admin.ModelAdmin):
    list_display = (
        "employee",
        "adjustment_type",
        "amount",
        "reason",
        "month",
        "date_created",
        "is_automatic",
    )
    list_filter = ("adjustment_type", "is_automatic", "date_created", "month", "employee__department")
    search_fields = ("employee__name", "employee__employee_id", "reason")
    readonly_fields = ("date_created",)
    fields = ("employee", "adjustment_type", "amount", "reason", "month", "comments", "is_automatic")
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Set default month to current month
        if not obj:
            from datetime import date
            form.base_fields['month'].initial = date.today().replace(day=1)
            form.base_fields['is_automatic'].initial = False
        return form


@admin.register(DashboardStub)
class DashboardStubAdmin(admin.ModelAdmin):
    def changelist_view(self, request, extra_context=None):
        from attendance.views import attendance_dashboard_view

        return attendance_dashboard_view(request)


@admin.register(SalaryReportStub)
class SalaryReportStubAdmin(admin.ModelAdmin):
    def changelist_view(self, request, extra_context=None):
        from attendance.views import salary_report_view

        return salary_report_view(request)
