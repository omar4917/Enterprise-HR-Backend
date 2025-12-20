from django.urls import path
from . import views

app_name = 'attendance'

urlpatterns = [
    path('api/validate-admin/', views.validate_admin_api, name='validate_admin_api'),
    path('api/employees/', views.employees_sync_api, name='employees_sync'),
    path('api/enroll/', views.enroll_employee_api, name='enroll_employee'),
    path('api/enroll-unknown/', views.enroll_unknown_employee_api, name='enroll_unknown'),
    path('api/check-in/', views.attendance_event_api, name='attendance_event'),
    path('api/livefeed/', views.livefeed_upload_api, name='livefeed_upload'),
    path('api/livefeed/<int:image_id>/', views.livefeed_delete_api, name='livefeed_delete_api'),
    path('api/voice-settings/', views.voice_settings_api, name='voice_settings_api'),
    path('api/message-settings/', views.message_settings_api, name='message_settings_api'),
    path('api/register-token/', views.register_token_api, name='register_token'),
    path('api/attendance/', views.attendance_api, name='attendance_api'),
    path('api/attendance-list/', views.attendance_list_api, name='attendance_list_api'),
    path('api/attendance-bulk-action/', views.attendance_bulk_action_api, name='attendance_bulk_action_api'),
    path('api/attendance-grid/', views.attendance_grid_api, name='attendance_grid_api'),
    path('api/holidays/', views.holidays_api, name='holidays_api'),
    path('api/salary-statistics/', views.salary_statistics_api, name='salary_statistics_api'),
    path('api/bulk-holidays-generate/', views.bulk_holiday_generate_api, name='bulk_holiday_generate_api'),
    path('api/salary-report/', views.salary_report_api, name='salary_report_api'),
    path('api/salary-report-detailed/', views.salary_report_detailed_api, name='salary_report_detailed_api'),
    path('api/salary-defaults/', views.salary_defaults_api, name='salary_defaults_api'),
    path('api/reports/', views.reports_api, name='reports_api'),
    path('api/livefeed-list/', views.livefeed_list_api, name='livefeed_list_api'),
    path('api/livefeed-action/', views.livefeed_action_api, name='livefeed_action_api'),
    path('api/moderator-labels/', views.moderator_labels_api, name='moderator_labels_api'),
    path('api/shifts/', views.shifts_api, name='shifts_api'),
    path('api/salary-defaults/', views.salary_defaults_api, name='salary_defaults_api'),
    path('api/company-info/', views.company_info_api, name='company_info_api'),
    path('api/context-settings/', views.context_settings_api, name='context_settings_api'),
    path('api/integration-settings/', views.integration_settings_api, name='integration_settings_api'),
    path('livefeed/', views.livefeed_view, name='livefeed'),
    path('employee/<int:employee_id>/', views.employee_detail_view, name='employee_detail'),
    path('device-sync/push/', views.push_employee_sync, name='push_employee_sync'),
    path('attendance-dashboard/pdf/', views.attendance_dashboard_pdf, name='attendance_dashboard_pdf'),
    path('attendance-dashboard/pdf/bulk/', views.attendance_dashboard_pdf_bulk, name='attendance_dashboard_pdf_bulk'),
    path('attendance-dashboard/pdf/combined/', views.attendance_dashboard_pdf_combined, name='attendance_dashboard_pdf_combined'),
    path('salary-report/pdf/', views.salary_report_pdf, name='salary_report_pdf'),
    path('moderator-edit/', views.moderator_edit_view, name='moderator_edit'),
    path('api/export/', views.export_api, name='export_api'),
    path('api/import/', views.import_api, name='import_api'),
    
    # Multi-tenant Organization management APIs
    path('api/organizations/', views.organizations_api, name='organizations_api'),
    path('api/organizations/<int:org_id>/', views.organization_detail_api, name='organization_detail_api'),
    path('api/organizations/<int:org_id>/stats/', views.organization_stats_api, name='organization_stats_api'),
    path('api/organizations/<int:org_id>/devices/', views.organization_devices_api, name='organization_devices_api'),
    
    # Device management APIs
    path('api/devices/', views.devices_api, name='devices_api'),
    path('api/devices/<int:device_id>/', views.device_detail_api, name='device_detail_api'),
    path('api/devices/validate/', views.device_validate_api, name='device_validate_api'),
    
    # Organization User management APIs
    path('api/org-users/', views.org_users_api, name='org_users_api'),
    path('api/org-users/<int:user_id>/', views.org_user_detail_api, name='org_user_detail_api'),
    
    # SaaS APIs: Audit Logs and Subscription Plans
    path('api/audit-logs/', views.audit_log_api, name='audit_log_api'),
    path('api/log-action/', views.log_action_api, name='log_action_api'),
    path('api/subscription-plans/', views.subscription_plans_api, name='subscription_plans_api'),
    
    # Data Export/Import (JSON format - for backups)
    path('api/export-data/', views.export_data_api, name='export_data_api'),
    path('api/import-data/', views.import_data_api, name='import_data_api'),
    
    # Analytics
    path('api/analytics/', views.analytics_api, name='analytics_api'),
]



