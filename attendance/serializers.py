"""
DRF Serializers for the Enterprise HR Backend.

These maintain the exact same JSON key contracts expected by the
Android APK (face recognition terminal) and PHP Dashboard.
"""

from rest_framework import serializers
from .models import (
    Organization, Employee, Shift, AttendanceRecord, Device,
    OrganizationUser, OrganizationSettings, BulkHoliday,
    IntegrationSetting, VoiceSetting, TextMessageSetting, ContextSetting,
    SalaryStatistic, SalaryStatisticDefault, SubscriptionPlan, AuditLog,
    LiveFeedImage, CompanyInfo, ModeratorLabel,
    VoiceNameOverride, VoicePhraseOverride, EmployeeVoicePreference,
)
from django.contrib.auth.models import User


# =============================================================================
# CORE SERIALIZERS
# =============================================================================

class OrganizationSerializer(serializers.ModelSerializer):
    employee_count = serializers.SerializerMethodField()
    device_count = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            'id', 'name', 'slug', 'email', 'phone', 'address', 'logo',
            'website', 'tin', 'bin', 'founder',
            'is_active', 'max_employees', 'max_devices', 'plan',
            'employee_count', 'device_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_employee_count(self, obj):
        return obj.employee_count()

    def get_device_count(self, obj):
        return obj.device_count()


class OrganizationSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationSettings
        fields = '__all__'


class EmployeeSerializer(serializers.ModelSerializer):
    """
    Serializer for Employee model.
    Preserves the exact JSON contract expected by the Android APK.
    """
    organization_name = serializers.SerializerMethodField()
    employee_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = [
            'id', 'employee_id', 'name', 'email', 'department', 'phone',
            'designation', 'bank_account', 'branch', 'employee_image',
            'employee_image_url', 'facial_template',
            'monthly_salary', 'is_active', 'date_inactive', 'hire_date',
            'organization', 'organization_name',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_organization_name(self, obj):
        return obj.organization.name if obj.organization else None

    def get_employee_image_url(self, obj):
        if obj.employee_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.employee_image.url)
            return obj.employee_image.url
        return None


class EmployeeListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views (no facial_template)."""
    organization_name = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = [
            'id', 'employee_id', 'name', 'email', 'department', 'phone',
            'designation', 'monthly_salary', 'is_active',
            'organization', 'organization_name',
        ]

    def get_organization_name(self, obj):
        return obj.organization.name if obj.organization else None


class ShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shift
        fields = [
            'id', 'name', 'shift_start', 'shift_end',
            'present_hours', 'half_day_hours', 'allowed_late_minutes',
            'absent_after_minutes',
            'late_override_status', 'late_override_minutes',
            'is_active', 'organization',
        ]


class AttendanceRecordSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    employee_id_str = serializers.SerializerMethodField()
    shift_name = serializers.SerializerMethodField()
    late_duration_display = serializers.SerializerMethodField()
    checkin_image_url = serializers.SerializerMethodField()
    checkout_image_url = serializers.SerializerMethodField()

    class Meta:
        model = AttendanceRecord
        fields = [
            'id', 'employee', 'employee_name', 'employee_id_str',
            'date', 'shift', 'shift_name',
            'checkin_time', 'checkout_time',
            'checkin_image', 'checkout_image',
            'checkin_image_url', 'checkout_image_url',
            'device_id', 'status', 'late_duration', 'late_duration_display',
            'is_status_override', 'organization',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at', 'late_duration']

    def get_employee_name(self, obj):
        return obj.employee.name if obj.employee else None

    def get_employee_id_str(self, obj):
        return obj.employee.employee_id if obj.employee else None

    def get_shift_name(self, obj):
        return obj.shift.name if obj.shift else None

    def get_late_duration_display(self, obj):
        if obj.late_duration:
            total_seconds = int(obj.late_duration.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            if hours > 0:
                return f"{hours}h {minutes}m"
            return f"{minutes}m"
        return None

    def get_checkin_image_url(self, obj):
        if obj.checkin_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.checkin_image.url)
            return obj.checkin_image.url
        return None

    def get_checkout_image_url(self, obj):
        if obj.checkout_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.checkout_image.url)
            return obj.checkout_image.url
        return None


class DeviceSerializer(serializers.ModelSerializer):
    organization_name = serializers.SerializerMethodField()

    class Meta:
        model = Device
        fields = [
            'id', 'device_id', 'device_name', 'location',
            'is_active', 'last_seen', 'organization', 'organization_name',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['last_seen', 'created_at', 'updated_at']

    def get_organization_name(self, obj):
        return obj.organization.name if obj.organization else None


# =============================================================================
# SETTINGS SERIALIZERS
# =============================================================================

class IntegrationSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntegrationSetting
        fields = '__all__'


class VoiceSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = VoiceSetting
        fields = '__all__'


class TextMessageSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = TextMessageSetting
        fields = '__all__'


class ContextSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContextSetting
        fields = '__all__'


# =============================================================================
# SALARY & HOLIDAY SERIALIZERS
# =============================================================================

class SalaryStatisticSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    employee_id_str = serializers.SerializerMethodField()

    class Meta:
        model = SalaryStatistic
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

    def get_employee_name(self, obj):
        return obj.employee.name if obj.employee else None

    def get_employee_id_str(self, obj):
        return obj.employee.employee_id if obj.employee else None


class SalaryStatisticDefaultSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalaryStatisticDefault
        fields = '__all__'


class BulkHolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = BulkHoliday
        fields = '__all__'
        read_only_fields = ['created_at']


# =============================================================================
# SAAS SERIALIZERS
# =============================================================================

class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = '__all__'
        read_only_fields = ['timestamp']


class OrganizationUserSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    organization_name = serializers.SerializerMethodField()

    class Meta:
        model = OrganizationUser
        fields = [
            'id', 'user', 'username', 'email',
            'organization', 'organization_name', 'role',
        ]

    def get_username(self, obj):
        return obj.user.username if obj.user else None

    def get_email(self, obj):
        return obj.user.email if obj.user else None

    def get_organization_name(self, obj):
        return obj.organization.name if obj.organization else "All Organizations"


# =============================================================================
# MISC SERIALIZERS
# =============================================================================

class LiveFeedImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = LiveFeedImage
        fields = [
            'id', 'organization', 'employee', 'subject_identifier',
            'image', 'image_url', 'device_id', 'captured_at', 'created_at',
        ]
        read_only_fields = ['created_at']

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class ModeratorLabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModeratorLabel
        fields = '__all__'
