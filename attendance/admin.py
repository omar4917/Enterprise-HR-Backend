# Django admin framework imports
from django.contrib import admin
from django import forms
from django.utils.html import format_html
from django.forms.widgets import SplitDateTimeWidget
from django.conf import settings
from django.urls import reverse
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _
from django.contrib.admin import helpers
from django.db import transaction
from django.forms import modelformset_factory, BaseModelFormSet
import pytz
from django.db.models import Window, F
from django.db.models.functions import RowNumber

# Local model imports
from .models import (
    Employee,
    AttendanceRecord,
    DashboardStub,
    LiveFeedStub,
    LiveFeedImage,
    Shift,
    SalaryReportStub,
    BulkHoliday,
    IntegrationSetting,
    VoiceSetting,
    TextMessageSetting,
    ContextSetting,
    MessageSetting,
    VoiceNameOverride,
    VoicePhraseOverride,
    EmployeeVoicePreference,
    SalaryStatistic,
    SalaryStatisticDefault,
    CompanyInfo,
    ModeratorLabel,
    # Multi-tenant models
    Organization,
    Device,
    OrganizationUser,
    OrganizationSettings,
)

# Timezone configuration
dhaka = pytz.timezone("Asia/Dhaka")

# Admin site branding
admin.site.site_header = "BaraBDOnline.XYZ"
admin.site.site_title = "barabdonline.xyz"
admin.site.index_title = "Welcome to barabdonline.xyz attendance Dashboard"


class HiddenFromIndexAdmin(admin.ModelAdmin):
    """
    Base admin to hide a model from the index while keeping direct URLs usable.
    """

    def get_model_perms(self, request):
        return {}


class UniqueEmployeePrefFormSet(BaseModelFormSet):
    """Ensure only one voice preference per employee in the formset."""

    def clean(self):
        super().clean()
        seen = set()
        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue
            if form.cleaned_data.get("DELETE"):
                continue
            emp = form.cleaned_data.get("employee")
            if not emp:
                continue
            if emp.pk in seen:
                raise forms.ValidationError(
                    _("Each employee can only have one voice preference.")
                )
            seen.add(emp.pk)


class AttendanceRecordForm(forms.ModelForm):
    """Custom form for attendance records with enhanced datetime widgets"""
    class Meta:
        model = AttendanceRecord
        fields = "__all__"
        widgets = {
            # Split datetime widgets for better UX
            "checkin_time": SplitDateTimeWidget(
                date_attrs={"type": "date"}, time_attrs={"type": "time"}
            ),
            "checkout_time": SplitDateTimeWidget(
                date_attrs={"type": "date"}, time_attrs={"type": "time"}
            ),
        }


class InputDateFilter(admin.SimpleListFilter):
    title = 'Date'
    parameter_name = 'date'
    template = 'admin/input_date_filter.html'

    def lookups(self, request, model_admin):
        # Dummy lookup to force the filter to appear
        return (('dummy', 'dummy'),)

    def choices(self, changelist):
        # Extract the current value from the query string
        value = self.value()
        return [{
            'selected': value is not None,
            'query_string': changelist.get_query_string({self.parameter_name: value}, [self.parameter_name]),
            'display': 'Date',
        }]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(date=self.value())
        return queryset


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    """Enhanced admin interface for attendance records with image previews"""
    form = AttendanceRecordForm
    list_display = (
        "row_index",
        "employee",
        "date",
        "formatted_checkin_time",
        "formatted_checkout_time",
        "status_display",
        "formatted_late_duration",
        "device_id",  # NEW
        "checkin_image_preview",
        "checkout_image_preview",
    )
    list_filter = (InputDateFilter, "status", "employee__department")
    search_fields = ("employee__employee_id", "employee__name", "device_id")
    readonly_fields = ("late_duration", "override_status_message", "is_status_override")
    fieldsets = (
        (None, {
            'fields': ('employee', 'date', 'shift')
        }),
        ('Time & Images', {
            'fields': (
                ('checkin_time', 'checkin_image'),
                ('checkout_time', 'checkout_image'),
                'device_id'
            )
        }),
        ('Status & Override', {
            'fields': (
                'status',
                'override_status_message',
                'late_duration',
                'is_status_override'
            )
        }),
    )
    actions = ['remove_checkout']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            row_position=Window(
                expression=RowNumber(),
                order_by=F(self.model._meta.pk.name).asc(),
            )
        )

    def row_index(self, obj):
        return getattr(obj, "row_position", "")

    row_index.short_description = "#"
    
    def remove_checkout(self, request, queryset):
        """Remove checkout time and image for selected records"""
        import os
        updated = 0
        for record in queryset:
            if record.checkout_time or record.checkout_image:
                # Remove checkout image file
                if record.checkout_image:
                    try:
                        if os.path.exists(record.checkout_image.path):
                            os.remove(record.checkout_image.path)
                    except:
                        pass
                    record.checkout_image = None
                
                # Remove checkout time
                record.checkout_time = None
                record.save()
                updated += 1
        
        self.message_user(request, f"Removed checkout for {updated} records.")
    
    remove_checkout.short_description = "Remove checkout time and image"

    def formatted_checkin_time(self, obj):
        """Display checkin time in dd/mm/yyyy format with Dhaka timezone"""
        if obj.checkin_time:
            return obj.checkin_time.astimezone(dhaka).strftime("%d/%m/%Y %I:%M %p")
        return "—"

    formatted_checkin_time.short_description = "Check-In Time"

    def formatted_checkout_time(self, obj):
        """Display checkout time in dd/mm/yyyy format with Dhaka timezone"""
        if obj.checkout_time:
            return obj.checkout_time.astimezone(dhaka).strftime("%d/%m/%Y %I:%M %p")
        return "—"

    formatted_checkout_time.short_description = "Check-Out Time"

    def formatted_late_duration(self, obj):
        """Display late duration in human-readable format (H:M:S or M:S)"""
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
        """Display thumbnail preview of checkin image"""
        if obj.checkin_image:
            return format_html(
                '<img src="{}" width="60" height="60" style="object-fit:cover;border-radius:5px;" />',
                obj.checkin_image.url,
            )
        return "—"

    checkin_image_preview.short_description = "Check-In Image"

    def checkout_image_preview(self, obj):
        """Display thumbnail preview of checkout image"""
        if obj.checkout_image:
            return format_html(
                '<img src="{}" width="60" height="60" style="object-fit:cover;border-radius:5px;" />',
                obj.checkout_image.url,
            )
        return "—"

    checkout_image_preview.short_description = "Check-Out Image"

    def status_display(self, obj):
        if obj.is_status_override:
            return format_html(
                '{} <span style="color:orange; font-weight:bold;" title="Manually Overridden">⚠️ (Manual)</span>',
                obj.status
            )
        return obj.status
    status_display.short_description = "Status"
    status_display.admin_order_field = "status"

    def override_status_message(self, obj):
        if obj.is_status_override:
            return format_html(
                '<div style="background: #fff3cd; color: #856404; padding: 10px; border: 1px solid #ffeeba; border-radius: 4px;">'
                '<strong>⚠️ Status Manually Overridden</strong><br>'
                'This status was manually set and will not be auto-calculated based on check-in/out times.'
                '</div>'
            )
        return ""
    override_status_message.short_description = "Override Status"

    def save_model(self, request, obj, form, change):
        if change:
            # Check if status was changed in the form
            if 'status' in form.changed_data:
                obj.is_status_override = True
                self.message_user(request, "Status manually overridden. Auto-calculation disabled for this record.", level="WARNING")
            
            # If times changed, reset override to allow re-calculation
            if 'checkin_time' in form.changed_data or 'checkout_time' in form.changed_data:
                obj.is_status_override = False
                self.message_user(request, "Time changed. Status auto-calculation re-enabled.", level="INFO")
        
        super().save_model(request, obj, form, change)

    class Media:
        css = {
            'all': ('admin/css/admin_sticky_headers.css',)
        }
        js = ("js/admin_date_filter_mover.js",)

@admin.register(LiveFeedImage)
class LiveFeedImageAdmin(admin.ModelAdmin):
    """Admin view for short-retention live feed images."""

    list_display = ("subject_identifier", "employee", "captured_at", "device_id", "image_preview")
    list_filter = ("employee__department", "device_id", "subject_identifier")
    search_fields = ("employee__employee_id", "employee__name", "device_id", "subject_identifier")
    readonly_fields = ("captured_at", "created_at", "image_preview", "subject_identifier")
    fields = ("employee", "subject_identifier", "device_id", "captured_at", "image", "image_preview", "created_at")
    ordering = ("-captured_at",)
    date_hierarchy = "captured_at"
    list_per_page = 50
    actions = ["purge_expired"]

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="80" height="80" style="object-fit:cover;border-radius:6px;" />',
                obj.image.url,
            )
        return "-"  # Empty placeholder

    image_preview.short_description = "Preview"

    def purge_expired(self, request, queryset):
        """Admin action to clean up images beyond retention window."""
        removed = LiveFeedImage.purge_older_than()
        self.message_user(request, f"Purged {removed} expired live feed images.")

    purge_expired.short_description = "Delete images older than retention window"

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            obj.delete()


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    """Employee admin with photo preview, face recognition support, and import/export"""
    list_display = (
        "row_index",
        "employee_image_tag",
        "employee_id",
        "name",
        "department",
        "designation",
        "monthly_salary",
        "is_active",
        "template_status",
    )
    search_fields = ("employee_id", "name", "department", "email")
    list_filter = ("is_active", "department", "designation")
    list_display_links = ("employee_id",)
    list_editable = ("is_active",)
    
    def changelist_view(self, request, extra_context=None):
        """Enhanced changelist with import/export functionality"""
        # Handle export
        if request.GET.get('export'):
            from .utils.import_helpers import export_employees
            return export_employees(request)
        
        # Handle import
        if request.method == 'POST' and request.FILES.get('import_file'):
            from .utils.import_helpers import import_employees
            import_errors, import_success = import_employees(request)
            
            if import_errors:
                from django.contrib import messages
                for error in import_errors:
                    messages.error(request, error)
            
            if import_success:
                from django.contrib import messages
                messages.success(request, f"Import successful! Created: {import_success['created']}, Updated: {import_success['updated']}")
        
        # Add import/export context
        if extra_context is None:
            extra_context = {}
        from .utils.import_helpers import HAS_OPENPYXL
        has_env_key = bool(getattr(settings, "FCM_SERVER_KEY", "").strip())
        has_env_service = bool(getattr(settings, "FCM_SERVICE_ACCOUNT_JSON", "").strip())
        try:
            has_db_key = IntegrationSetting.objects.exclude(fcm_server_key="").exists()
            has_db_service = IntegrationSetting.objects.exclude(fcm_service_account_json="").exists()
        except Exception:
            has_db_key = False
            has_db_service = False
        extra_context.update({
            'has_openpyxl': HAS_OPENPYXL,
            'show_import_export': True,
            'fcm_key_missing': not (has_env_key or has_env_service or has_db_key or has_db_service),
        })
        
        return super().changelist_view(request, extra_context)
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            row_position=Window(
                expression=RowNumber(),
                order_by=F(self.model._meta.pk.name).asc(),
            )
        )

    def row_index(self, obj):
        return getattr(obj, "row_position", "")

    row_index.short_description = "#"

    def employee_image_tag(self, obj):
        """Display circular employee photo thumbnail with fallback"""
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
    
    def template_status(self, obj):
        """Display client-side template sync status"""
        if obj.facial_template:
            return format_html('<span style="color:green;">Synced</span>')
        return format_html('<span style="color:red;">Missing</span>')

    template_status.short_description = "Template Synced"


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    """Shift configuration admin with inline editing"""
    list_display = (
        "name",
        "shift_start",
        "shift_end",
        "present_hours",
        "half_day_hours",
        "allowed_late_minutes",
        "late_override_minutes",
        "late_override_status",
        "enable_late_status",
        "is_active",
    )
    list_editable = ("is_active",)
    search_fields = ("name",)





@admin.register(SalaryStatistic)
class SalaryStatisticAdmin(admin.ModelAdmin):
    list_display = (
        "row_index",
        "employee",
        "month",
        "year",
        "basic_salary",
        "gross_salary",
        "payable",
        "late_fine",
        "attendance_bonus",
        "tds_percent",
        "use_default",
    )
    list_filter = ("year", "month", "employee__department")
    search_fields = ("employee__name", "employee__employee_id")
    readonly_fields = ("created_at", "updated_at")
    change_list_template = "admin/salary_statistic_change_list.html"
    fieldsets = (
        (None, {
            'fields': ('employee', 'month', 'year', 'use_default')
        }),
        ('Salary Components', {
            'fields': (
                'basic_salary', 'house_rent', 'medical_allowance', 
                'conveyance_allowance', 'food_allowance', 'other_allowance',
                'gross_salary'
            )
        }),
        ('Attendance & Overtime', {
            'fields': (
                'working_days', 'weekends', 'leave_days', 'holidays', 'attended_days',
                'ot_hours', 'ot_rate', 'ot_amount', 'hd_allowance'
            )
        }),
        ("Adjustments", {
            "fields": (
                "attendance_bonus",
                "required_attendance_percent",
                "late_fine",
                "late_needed",
                "other_deduction",
            )
        }),
        ("Deductions", {
            "fields": ("tds_percent", "stamp", "payable")
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at")
        })
    )

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom = [
            path("reload/", self.admin_site.admin_view(self.reload_missing), name="salary_stats_reload"),
        ]
        return custom + urls

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            row_position=Window(
                expression=RowNumber(),
                order_by=F(self.model._meta.pk.name).asc(),
            )
        )

    def row_index(self, obj):
        return getattr(obj, "row_position", "")

    row_index.short_description = "#"

    def reload_missing(self, request):
        from .views import _ensure_salary_statistics
        from datetime import datetime
        now = datetime.now()
        year = int(request.GET.get("year", now.year))
        month = int(request.GET.get("month", now.month))
        # only create missing stats; do not alter existing
        employees = Employee.objects.all()
        existing_keys = set(
            SalaryStatistic.objects.filter(month=month, year=year).values_list("employee_id", flat=True)
        )
        missing = employees.exclude(id__in=existing_keys)
        import calendar
        days_in_month = calendar.monthrange(year, month)[1]
        _ensure_salary_statistics(year, month, missing, days_in_month)
        self.message_user(request, f"Reloaded {missing.count()} missing salary stats for {month}/{year}.")
        from django.shortcuts import redirect
        return redirect("admin:attendance_salarystatistic_changelist")


@admin.register(SalaryStatisticDefault)
class SalaryStatisticDefaultAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "basic_salary_display",
        "house_rent",
        "medical_allowance",
        "conveyance_allowance",
        "attendance_bonus",
        "late_fine",
    )
    
    def basic_salary_display(self, obj):
        return "Synced from Employee"
    basic_salary_display.short_description = "Basic Salary"


@admin.register(ModeratorLabel)
class ModeratorLabelAdmin(admin.ModelAdmin):
    list_display = ("key", "label", "updated_at")
    search_fields = ("key", "label")

    fieldsets = (
        ("Allowances", {
            "fields": (
                "house_rent",
                "medical_allowance",
                "conveyance_allowance",
                "food_allowance",
                "other_allowance",
                "hd_allowance",
            )
        }),
        ("Overtime", {
            "fields": ("ot_rate",)
        }),
        ("Adjustments", {
            "fields": (
                "attendance_bonus",
                "required_attendance_percent",
                "late_fine",
                "late_needed",
            )
        }),
        ("Deductions", {
            "fields": ("tds_percent", "stamp")
        }),
    )


@admin.register(LiveFeedStub)
class LiveFeedStubAdmin(admin.ModelAdmin):
    """Redirect admin to the live feed page"""

    def changelist_view(self, request, extra_context=None):
        from attendance.views import livefeed_view
        return livefeed_view(request)


@admin.register(DashboardStub)
class DashboardStubAdmin(admin.ModelAdmin):
    """Redirect admin to custom dashboard view"""
    def changelist_view(self, request, extra_context=None):
        """Override changelist to show custom dashboard"""
        from attendance.views import attendance_dashboard_view
        return attendance_dashboard_view(request)


@admin.register(SalaryReportStub)
class SalaryReportStubAdmin(admin.ModelAdmin):
    """Redirect admin to custom salary report view"""
    def changelist_view(self, request, extra_context=None):
        """Override changelist to show custom salary report"""
        from attendance.views import salary_report_view
        return salary_report_view(request)


@admin.register(BulkHoliday)
class BulkHolidayAdmin(admin.ModelAdmin):
    """Simplified Holiday management admin"""
    list_display = (
        "name",
        "start_date",
        "end_date",
        "is_active",
        "is_government",
        "created_at",
    )
    list_filter = ("is_active", "is_government", "created_at")
    search_fields = ("name",)
    readonly_fields = ("created_at", "created_by")
    list_editable = ("is_active",)
    
    fieldsets = (
        (None, {
            'fields': ('name', 'start_date', 'end_date')
        }),
        ('Settings', {
            'fields': ('is_active', 'is_government')
        }),
        ('Info', {
            'fields': ('created_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def delete_model(self, request, obj):
        """Custom delete to trigger attendance record cleanup"""
        obj.delete()
    
    def delete_queryset(self, request, queryset):
        """Custom bulk delete to trigger attendance record cleanup"""
        for obj in queryset:
            obj.delete()


@admin.register(IntegrationSetting)
class IntegrationSettingAdmin(admin.ModelAdmin):
    """Admin form for integration credentials (FCM server key)."""
    fields = ("fcm_server_key", "fcm_service_account_json", "updated_at")
    readonly_fields = ("updated_at",)

    def has_add_permission(self, request):
        if IntegrationSetting.objects.exists():
            return False
        return super().has_add_permission(request)


@admin.register(VoiceSetting)
class VoiceSettingAdmin(admin.ModelAdmin):
    """Admin for voice/TTS configuration exposed to the Android app."""

    list_display = ("default_language", "name_format", "voice_mode", "updated_at")
    readonly_fields = ("updated_at",)
    change_form_template = "admin/attendance/voice_setting_change_form.html"
    fieldsets = (
        ("Language", {
            "fields": ("default_language", "additional_languages")
        }),
        ("Voice", {
            "fields": ("speech_rate", "pitch", "voice_mode", "voice_repeat_delay_seconds")
        }),
        ("Name format", {
            "fields": ("name_format", "custom_name_template")
        }),
        ("Metadata", {"fields": ("updated_at",)}),
    )

    def has_add_permission(self, request):
        if VoiceSetting.objects.exists():
            return False
        return super().has_add_permission(request)

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        """
        Custom change form that embeds voice overrides and preferences formsets
        on the same page as the base voice settings.
        """
        extra_context = extra_context or {}
        obj = self.get_object(request, object_id)
        if obj is None and VoiceSetting.objects.exists():
            # Fallback to the singleton if URL missing
            obj = VoiceSetting.get_solo()
            object_id = str(obj.pk)

        NameFormSet = modelformset_factory(
            VoiceNameOverride,
            fields=("employee", "language_code", "spoken_name"),
            extra=0,
            can_delete=True,
            widgets={
                "language_code": forms.TextInput(
                    attrs={
                        "title": "e.g. en-US (English), bn-BD (Bangla), hi-IN (Hindi), ar-SA, fr-FR, es-ES, de-DE, ja-JP, ko-KR, zh-CN",
                        "placeholder": "en-US",
                    }
                )
            },
        )
        PhraseFormSet = modelformset_factory(
            VoicePhraseOverride,
            fields=("language_code", "checkin_phrase", "checkout_phrase", "is_active"),
            extra=0,
            can_delete=True,
            widgets={
                "language_code": forms.TextInput(
                    attrs={
                        "title": "e.g. en-US (English), bn-BD (Bangla), hi-IN (Hindi), ar-SA, fr-FR, es-ES, de-DE, ja-JP, ko-KR, zh-CN",
                        "placeholder": "en-US",
                    }
                )
            },
        )
        PrefFormSet = modelformset_factory(
            EmployeeVoicePreference,
            fields=("employee", "language_code"),
            extra=0,
            can_delete=True,
            formset=UniqueEmployeePrefFormSet,
            widgets={
                "language_code": forms.TextInput(
                    attrs={
                        "title": "e.g. en-US (English), bn-BD (Bangla), hi-IN (Hindi), ar-SA, fr-FR, es-ES, de-DE, ja-JP, ko-KR, zh-CN",
                        "placeholder": "en-US",
                    }
                )
            },
        )

        ModelForm = self.get_form(request, obj, change=bool(obj))
        if request.method == "POST":
            form = ModelForm(request.POST, request.FILES, instance=obj)
            name_fs = NameFormSet(request.POST, prefix="names", queryset=VoiceNameOverride.objects.all())
            phrase_fs = PhraseFormSet(request.POST, prefix="phrases", queryset=VoicePhraseOverride.objects.all())
            pref_fs = PrefFormSet(request.POST, prefix="prefs", queryset=EmployeeVoicePreference.objects.all())

            form_valid = form.is_valid()
            name_valid = name_fs.is_valid()
            phrase_valid = phrase_fs.is_valid()
            pref_valid = pref_fs.is_valid()

            if form_valid and name_valid and phrase_valid and pref_valid:
                with transaction.atomic():
                    obj = form.save()
                    for fs in (name_fs, phrase_fs, pref_fs):
                        instances = fs.save(commit=False)
                        for deleted in fs.deleted_objects:
                            deleted.delete()
                        for inst in instances:
                            if isinstance(inst, VoiceNameOverride):
                                inst.is_active = True
                            inst.save()
                change_message = _("Voice settings and overrides were saved.")
                self.log_change(request, obj, change_message)
                messages.success(request, change_message)
                return HttpResponseRedirect(
                    reverse("admin:attendance_voicesetting_change", args=[obj.pk])
                )
        else:
            form = ModelForm(instance=obj)
            name_fs = NameFormSet(prefix="names", queryset=VoiceNameOverride.objects.all())
            phrase_fs = PhraseFormSet(prefix="phrases", queryset=VoicePhraseOverride.objects.all())
            pref_fs = PrefFormSet(prefix="prefs", queryset=EmployeeVoicePreference.objects.all())

        admin_form = helpers.AdminForm(
            form,
            self.get_fieldsets(request, obj),
            prepopulated_fields=self.get_prepopulated_fields(request, obj),
            readonly_fields=self.get_readonly_fields(request, obj),
            model_admin=self,
        )

        media = self.media + admin_form.media
        for fs in (name_fs, phrase_fs, pref_fs):
            media = media + fs.media

        context = {
            **self.admin_site.each_context(request),
            "title": _("Change %s") % self.model._meta.verbose_name,
            "adminform": admin_form,
            "errors": helpers.AdminErrorList(form, ()),
            "is_popup": False,
            "save_as": self.save_as,
            "has_add_permission": self.has_add_permission(request),
            "has_change_permission": self.has_change_permission(request, obj),
            "has_view_permission": self.has_view_permission(request, obj),
            "has_delete_permission": self.has_delete_permission(request, obj),
            "has_editable_inline_admin_formsets": True,
            "add": False,
            "change": True,
            "object_id": object_id,
            "original": obj,
            "opts": self.model._meta,
            "app_label": self.model._meta.app_label,
            "media": media,
            "name_formset": name_fs,
            "phrase_formset": phrase_fs,
            "pref_formset": pref_fs,
        }

        return TemplateResponse(
            request,
            self.change_form_template or [
                "admin/%s/%s/change_form.html" % (self.model._meta.app_label, self.model._meta.model_name),
                "admin/%s/change_form.html" % self.model._meta.app_label,
                "admin/change_form.html",
            ],
            context,
        )


@admin.register(TextMessageSetting)
class TextMessageSettingAdmin(admin.ModelAdmin):
    """Admin for text message templates and intervals."""
    list_display = ("checkin_text", "checkout_text", "checkin_active", "checkout_active", "updated_at")
    readonly_fields = ("updated_at",)

    def has_add_permission(self, request):
        if TextMessageSetting.objects.exists():
            return False
        return super().has_add_permission(request)


@admin.register(ContextSetting)
class ContextSettingAdmin(admin.ModelAdmin):
    list_display = ("text_message_display", "voice_message_active", "updated_at")
    readonly_fields = ("updated_at",)

    def has_add_permission(self, request):
        if ContextSetting.objects.exists():
            return False
        return super().has_add_permission(request)


@admin.register(VoiceNameOverride)
class VoiceNameOverrideAdmin(HiddenFromIndexAdmin):
    list_display = ("employee", "language_code", "spoken_name", "is_active", "updated_at")
    list_filter = ("language_code", "is_active")
    search_fields = ("employee__employee_id", "employee__name", "language_code", "spoken_name")
    readonly_fields = ("updated_at",)


@admin.register(VoicePhraseOverride)
class VoicePhraseOverrideAdmin(HiddenFromIndexAdmin):
    list_display = ("language_code", "is_active", "updated_at")
    list_filter = ("language_code", "is_active")
    readonly_fields = ("updated_at",)


@admin.register(EmployeeVoicePreference)
class EmployeeVoicePreferenceAdmin(HiddenFromIndexAdmin):
    list_display = ("employee", "language_code", "updated_at")
    list_filter = ("language_code",)
    search_fields = ("employee__employee_id", "employee__name", "language_code")
    readonly_fields = ("updated_at",)


@admin.register(CompanyInfo)
class CompanyInfoAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "phone", "tin", "bin", "founder")
    
    def has_add_permission(self, request):
        # Only allow adding if no instance exists
        if self.model.objects.exists():
            return False
        return super().has_add_permission(request)


# =============================================================================
# MULTI-TENANT ADMIN
# =============================================================================

class DeviceInline(admin.TabularInline):
    """Inline device management within Organization admin"""
    model = Device
    extra = 1
    fields = ('device_id', 'device_name', 'location', 'is_active', 'last_seen')
    readonly_fields = ('last_seen',)


class OrganizationSettingsInline(admin.StackedInline):
    """Inline settings within Organization admin"""
    model = OrganizationSettings
    can_delete = False
    verbose_name_plural = 'Settings'


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    """Admin for managing organizations (companies) in the multi-tenant system"""
    list_display = (
        'name',
        'slug',
        'employee_count',
        'device_count',
        'max_employees',
        'max_devices',
        'is_active',
        'created_at',
    )
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'slug', 'email')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')
    inlines = [DeviceInline, OrganizationSettingsInline]
    
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'is_active')
        }),
        ('Contact Information', {
            'fields': ('email', 'phone', 'address', 'logo')
        }),
        ('Limits', {
            'fields': ('max_employees', 'max_devices'),
            'description': 'License limits for this organization'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    """Admin for managing devices linked to organizations"""
    list_display = (
        'device_id',
        'device_name',
        'organization',
        'location',
        'is_active',
        'last_seen',
    )
    list_filter = ('organization', 'is_active')
    search_fields = ('device_id', 'device_name', 'organization__name', 'location')
    readonly_fields = ('last_seen', 'created_at', 'updated_at')
    
    fieldsets = (
        (None, {
            'fields': ('organization', 'device_id', 'device_name', 'location', 'is_active')
        }),
        ('Status', {
            'fields': ('last_seen', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(OrganizationUser)
class OrganizationUserAdmin(admin.ModelAdmin):
    """Admin for managing user-organization associations"""
    list_display = ('user', 'organization', 'role')
    list_filter = ('role', 'organization')
    search_fields = ('user__username', 'user__email', 'organization__name')
    raw_id_fields = ('user',)


@admin.register(OrganizationSettings)
class OrganizationSettingsAdmin(admin.ModelAdmin):
    """Admin for per-organization settings"""
    list_display = ('organization', 'timezone', 'voice_enabled', 'email_on_late')
    list_filter = ('timezone', 'voice_enabled')
    search_fields = ('organization__name',)




