from django.urls import path
from . import views

app_name = 'attendance'

urlpatterns = [
    path('api/employees/', views.employees_sync_api, name='employees_sync'),
    path('api/enroll/', views.enroll_employee_api, name='enroll_employee'),
    path('api/enroll-unknown/', views.enroll_unknown_employee_api, name='enroll_unknown'),
    path('api/check-in/', views.attendance_event_api, name='attendance_event'),
    path('api/livefeed/', views.livefeed_upload_api, name='livefeed_upload'),
    path('api/livefeed/<int:image_id>/', views.livefeed_delete_api, name='livefeed_delete_api'),
    path('api/voice-settings/', views.voice_settings_api, name='voice_settings_api'),
    path('api/message-settings/', views.message_settings_api, name='message_settings_api'),
    path('api/register-token/', views.register_token_api, name='register_token'),
    path('livefeed/', views.livefeed_view, name='livefeed'),
    path('employee/<int:employee_id>/', views.employee_detail_view, name='employee_detail'),
    path('device-sync/push/', views.push_employee_sync, name='push_employee_sync'),
    path('attendance-dashboard/pdf/', views.attendance_dashboard_pdf, name='attendance_dashboard_pdf'),
    path('attendance-dashboard/pdf/bulk/', views.attendance_dashboard_pdf_bulk, name='attendance_dashboard_pdf_bulk'),
    path('attendance-dashboard/pdf/combined/', views.attendance_dashboard_pdf_combined, name='attendance_dashboard_pdf_combined'),
    path('salary-report/pdf/', views.salary_report_pdf, name='salary_report_pdf'),
    path('moderator-edit/', views.moderator_edit_view, name='moderator_edit'),
]
