from django.urls import path
from . import views

app_name = 'attendance'

urlpatterns = [
    path('api/employees/', views.employees_sync_api, name='employees_sync'),
    path('api/enroll/', views.enroll_employee_api, name='enroll_employee'),
    path('api/enroll-unknown/', views.enroll_unknown_employee_api, name='enroll_unknown'),
    path('api/check-in/', views.attendance_event_api, name='attendance_event'),
    path('api/register-token/', views.register_token_api, name='register_token'),
    path('employee/<int:employee_id>/', views.employee_detail_view, name='employee_detail'),
    path('device-sync/push/', views.push_employee_sync, name='push_employee_sync'),
    path('attendance-dashboard/pdf/', views.attendance_dashboard_pdf, name='attendance_dashboard_pdf'),
    path('salary-report/pdf/', views.salary_report_pdf, name='salary_report_pdf'),
]
