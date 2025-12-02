from functools import lru_cache
from django.apps import apps

DEFAULT_LABELS = {
    "attendance_dashboard_title": "Attendance Dashboard",
    "attendance_employee_header": "Employee",
    "attendance_totals_label": "Totals",
    "employee_designation_header": "Designation",
    "attendance_present_header": "Total Present",
    "attendance_late_header": "Late",
    "attendance_leave_header": "On Leave",
    "attendance_holiday_header": "Holiday",
    "attendance_absent_header": "Absent",
    "attendance_halfday_header": "Half Day",
    "attendance_earlyleave_header": "Early Leave",
    "salary_report_title": "Salary Report",
    "salary_employee_header": "Employee",
    "salary_joining_header": "Join Date",
    "salary_bank_header": "Bank",
    "salary_basic_header": "Basic",
    "salary_house_rent_header": "House Rent",
    "salary_medical_header": "Medical",
    "salary_conveyance_header": "Conv",
    "salary_food_header": "Food",
    "salary_other_header": "Other Allow",
    "salary_gross_header": "Gross",
    "salary_totals_label": "Totals",
    "label_shifts": "Shifts",
    "label_employees": "Employees",
    "label_salary_statistics": "Salary Statistics",
    "label_attendance_records": "Attendance Records",
    "label_dashboard": "Dashboard",
    "label_salary_report": "Salary Report",
    "label_attendance_dashboard": "Attendance Dashboard",
}


@lru_cache(maxsize=256)
def _get_db_value(key):
    Model = apps.get_model("attendance", "ModeratorLabel")
    try:
        record = Model.objects.get(key=key)
        return (record.label or "").strip()
    except Model.DoesNotExist:
        return ""


def get_label(key, fallback=None):
    default = DEFAULT_LABELS.get(key, fallback or key.replace("_", " ").title())
    override = _get_db_value(key)
    return override or default


def clear_label_cache():
    _get_db_value.cache_clear()
