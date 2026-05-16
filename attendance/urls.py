from django.urls import path
from . import views

app_name = 'attendance'

# Only non-API template/view routes remain here.
# All API endpoints are now served by DRF ViewSets via api_urls.py
urlpatterns = [
    # Template-based views (admin dashboard, PDF exports, etc.)
    path('livefeed/', views.livefeed_view, name='livefeed'),
    path('employee/<int:employee_id>/', views.employee_detail_view, name='employee_detail'),
    path('device-sync/push/', views.push_employee_sync, name='push_employee_sync'),
    path('attendance-dashboard/pdf/', views.attendance_dashboard_pdf, name='attendance_dashboard_pdf'),
    path('attendance-dashboard/pdf/bulk/', views.attendance_dashboard_pdf_bulk, name='attendance_dashboard_pdf_bulk'),
    path('attendance-dashboard/pdf/combined/', views.attendance_dashboard_pdf_combined, name='attendance_dashboard_pdf_combined'),
    path('salary-report/pdf/', views.salary_report_pdf, name='salary_report_pdf'),
    path('moderator-edit/', views.moderator_edit_view, name='moderator_edit'),

    # Legacy endpoints kept for Android APK compatibility (face recognition)
    path('api/validate-admin/', views.validate_admin_api, name='validate_admin_api'),
    path('api/enroll/', views.enroll_employee_api, name='enroll_employee'),
    path('api/enroll-unknown/', views.enroll_unknown_employee_api, name='enroll_unknown'),
    path('api/check-in/', views.attendance_event_api, name='attendance_event'),
    path('api/livefeed/', views.livefeed_upload_api, name='livefeed_upload'),
    path('api/register-token/', views.register_token_api, name='register_token'),
]
