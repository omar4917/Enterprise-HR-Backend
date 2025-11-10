import calendar
from datetime import date
from urllib.parse import urlencode
from django.urls import reverse

from ..models import AttendanceRecord, Employee


def get_dashboard_params(request):
    """Read selected month/year & filters from request."""
    selected_month = int(request.GET.get("month", date.today().month))
    selected_year = int(request.GET.get("year", date.today().year))
    selected_department = request.GET.get("department") or None
    selected_designation = request.GET.get("designation") or None
    today = date.today()
    days_in_month = calendar.monthrange(selected_year, selected_month)[1]
    return (
        selected_year,
        selected_month,
        selected_department,
        selected_designation,
        today,
        days_in_month,
    )


def build_month_nav(
    selected_year, selected_month, selected_department, selected_designation
):
    """Build prev/next month querystrings."""

    def prev_month(y, m):
        return (y - 1, 12) if m == 1 else (y, m - 1)

    def next_month(y, m):
        return (y + 1, 1) if m == 12 else (y, m + 1)

    py, pm = prev_month(selected_year, selected_month)
    ny, nm = next_month(selected_year, selected_month)

    base_prev = {"month": pm, "year": py}
    base_next = {"month": nm, "year": ny}

    if selected_department:
        base_prev["department"] = selected_department
        base_next["department"] = selected_department
    if selected_designation:
        base_prev["designation"] = selected_designation
        base_next["designation"] = selected_designation

    prev_qs = urlencode(base_prev)
    next_qs = urlencode(base_next)
    return prev_qs, next_qs


def build_days(selected_year, selected_month, days_in_month):
    """Return list of day metadata dicts for the month."""
    days = []
    for d in range(1, days_in_month + 1):
        current = date(selected_year, selected_month, d)
        days.append(
            {
                "num": d,
                "short": current.strftime("%a"),
                "full": current.strftime("%A"),
                "iso": current.isoformat(),
            }
        )
    return days


def get_employee_queryset(selected_department, selected_designation):
    """Apply department/designation filters for Employee queryset."""
    employee_filter = {}
    if selected_department:
        employee_filter["department"] = selected_department
    if selected_designation:
        employee_filter["designation"] = selected_designation

    if employee_filter:
        return Employee.objects.filter(**employee_filter)
    return Employee.objects.all()


def build_record_map(selected_year, selected_month):
    """Return dict[(employee_id, day)] -> AttendanceRecord."""
    records = AttendanceRecord.objects.filter(
        date__year=selected_year, date__month=selected_month
    ).select_related("employee")
    return {(r.employee.id, r.date.day): r for r in records}


ICON_MAP = {
    "Present": "icons/present.png",
    "Absent": "icons/absent.png",
    "Early Leave": "icons/early_leave.png",
    "Half Day": "icons/half_day.png",
    "On Leave": "icons/on_leave.png",
    "Holiday": "icons/holidays.png",
    "Pending": "icons/pendings.png",
    "Off Day": "icons/off_day.png",
    "Late": "icons/late.png",
}


def build_employee_row(emp, days, today, record_map, active_shift):
    """
    Build one employee's dashboard row:
    returns (statuses, totals, emp_image_url)
    """
    statuses = []
    totals = {
        "Present": 0,
        "Late": 0,
        "On_Leave": 0,
        "Holiday": 0,
        "Absent": 0,
        "Half_Day": 0,
        "Early_Leave": 0,
    }

    # employee image url
    emp_image_url = None
    try:
        img_field = getattr(emp, "employee_image", None)
        if img_field and hasattr(img_field, "url"):
            emp_image_url = img_field.url
    except Exception:
        emp_image_url = None

    for day_info in days:
        day_num = day_info["num"]
        current_date = date(
            int(day_info["iso"].split("-")[0]),
            int(day_info["iso"].split("-")[1]),
            day_num,
        )
        record = record_map.get((emp.id, day_num), None)

        # Friday = Off Day (weekly off)
        if current_date.weekday() == 4:
            display_status = "Off Day"
            icon = ICON_MAP.get(display_status, "icons/pendings.png")
            is_late = False
            late_display = None
            change_url = None
            list_url = None
        else:
            if record is None:
                # Future -> blank
                if current_date > today:
                    display_status = None
                    icon = None
                    is_late = False
                    late_display = None
                    change_url = None
                    list_url = None
                else:
                    # Past/today without record -> Absent
                    display_status = "Absent"
                    icon = ICON_MAP.get(display_status, "icons/absent.png")
                    is_late = False
                    late_display = None
                    change_url = None
                    try:
                        base = reverse("admin:attendance_attendancerecord_changelist")
                    except Exception:
                        base = "/admin/attendance/attendancerecord/"
                    query = urlencode(
                        {
                            "employee__id__exact": emp.id,
                            "date": current_date.isoformat(),
                        }
                    )
                    list_url = f"{base}?{query}"
            else:
                # Compute status & late
                manual_statuses = ["On Leave", "Holiday", "Off Day"]
                stored_status = getattr(record, "status", None)

                try:
                    computed_late = record._compute_late_duration(active_shift)
                except Exception:
                    computed_late = None

                try:
                    computed_status = record.compute_status()
                except Exception:
                    computed_status = stored_status or "Pending"

                if stored_status in manual_statuses and stored_status:
                    display_status = stored_status
                else:
                    display_status = computed_status or stored_status or "Pending"

                icon = ICON_MAP.get(display_status, "icons/pendings.png")

                try:
                    change_url = reverse(
                        "admin:attendance_attendancerecord_change",
                        args=(record.pk,),
                    )
                except Exception:
                    change_url = None
                list_url = None

                try:
                    is_late = record.is_late_indicator()
                except Exception:
                    is_late = False

                late_display = None
                if computed_late:
                    try:
                        total = int(computed_late.total_seconds())
                        hours, rem = divmod(total, 3600)
                        minutes, seconds = divmod(rem, 60)
                        late_display = (
                            f"{hours:d}:{minutes:02d}:{seconds:02d}"
                            if hours
                            else f"{minutes:d}:{seconds:02d}"
                        )
                    except Exception:
                        late_display = None

        # update totals - count late indicators separately
        if display_status == "Present":
            totals["Present"] += 1
        elif display_status == "On Leave":
            totals["On_Leave"] += 1
        elif display_status == "Holiday":
            totals["Holiday"] += 1
        elif display_status == "Absent":
            totals["Absent"] += 1
        elif display_status == "Half Day":
            totals["Half_Day"] += 1
        elif display_status == "Early Leave":
            totals["Early_Leave"] += 1
        
        # Count late indicators (separate from status)
        if is_late:
            totals["Late"] += 1

        statuses.append(
            {
                "day": day_num,
                "status": display_status,
                "icon": icon,
                "change_url": change_url,
                "list_url": list_url,
                "is_late": is_late,
                "late_display": late_display,
            }
        )

    return statuses, totals, emp_image_url