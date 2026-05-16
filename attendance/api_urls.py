"""
DRF Router configuration for the Enterprise HR Backend.

All new DRF ViewSets are registered here. The legacy function-based
views in urls.py remain untouched during migration.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .api_views import (
    OrganizationViewSet, EmployeeViewSet, ShiftViewSet,
    AttendanceRecordViewSet, DeviceViewSet,
    OrganizationUserViewSet,
    IntegrationSettingViewSet, VoiceSettingViewSet,
    TextMessageSettingViewSet, ContextSettingViewSet,
    SalaryStatisticViewSet, SalaryStatisticDefaultViewSet,
    BulkHolidayViewSet, SubscriptionPlanViewSet, AuditLogViewSet,
    LiveFeedImageViewSet, ModeratorLabelViewSet,
)

router = DefaultRouter()

# Core resources
router.register(r'organizations', OrganizationViewSet, basename='organization')
router.register(r'employees', EmployeeViewSet, basename='employee')
router.register(r'shifts', ShiftViewSet, basename='shift')
router.register(r'attendance', AttendanceRecordViewSet, basename='attendance')
router.register(r'devices', DeviceViewSet, basename='device')

# Settings (singleton)
router.register(r'integration-settings', IntegrationSettingViewSet, basename='integration-setting')
router.register(r'voice-settings', VoiceSettingViewSet, basename='voice-setting')
router.register(r'text-message-settings', TextMessageSettingViewSet, basename='text-message-setting')
router.register(r'context-settings', ContextSettingViewSet, basename='context-setting')

# Salary & Holidays
router.register(r'salary-statistics', SalaryStatisticViewSet, basename='salary-statistic')
router.register(r'salary-defaults', SalaryStatisticDefaultViewSet, basename='salary-default')
router.register(r'holidays', BulkHolidayViewSet, basename='holiday')

# SaaS
router.register(r'subscription-plans', SubscriptionPlanViewSet, basename='subscription-plan')
router.register(r'audit-logs', AuditLogViewSet, basename='audit-log')

# Users & Misc
router.register(r'org-users', OrganizationUserViewSet, basename='org-user')
router.register(r'livefeed-images', LiveFeedImageViewSet, basename='livefeed-image')
router.register(r'moderator-labels', ModeratorLabelViewSet, basename='moderator-label')

urlpatterns = [
    path('', include(router.urls)),
]
