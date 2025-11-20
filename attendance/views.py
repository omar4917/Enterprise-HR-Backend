# Django framework imports
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from decimal import Decimal
from django.core.files.base import ContentFile
from django.utils.crypto import get_random_string
from django.utils import timezone
import base64
import json
import math
from datetime import timedelta

# Local app imports
from .models import (
    Employee,
    AttendanceRecord,
    DeviceRegistration,
    get_active_shift,
    SalaryAdjustment,
    BulkHoliday,
    dhaka_now,
)

# Utility modules for organized functionality
from .utils.dashboard_helpers import (
    get_dashboard_params,
    build_month_nav,
    build_days,
    get_employee_queryset,
    build_record_map,
    build_employee_row,
)
from .utils.import_helpers import handle_import, handle_export, HAS_OPENPYXL
from .utils.push_helpers import send_database_update_notification
from .utils.salary_helpers import (
    get_employee_salary_summary,
    process_monthly_salary_adjustments,
)

ATTENDANCE_COOLDOWN = timedelta(hours=1)
from reportlab.lib.pagesizes import A4, A3, A2, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch


@staff_member_required
def attendance_dashboard_view(request):
    """
    Main attendance dashboard with comprehensive features.
    
    Features:
    - Monthly attendance grid view with status icons
    - Department/designation filtering
    - Month-to-month navigation with preserved filters
    - Import/export functionality (CSV, XLSX, ZIP)
    - Real-time attendance totals and late indicators
    - Employee photo integration
    
    Returns: Rendered dashboard template with context data
    """
    (
        selected_year,
        selected_month,
        selected_department,
        selected_designation,
        today,
        days_in_month,
    ) = get_dashboard_params(request)

    prev_qs, next_qs = build_month_nav(
        selected_year,
        selected_month,
        selected_department,
        selected_designation,
    )

    # Export block
    export_response = handle_export(request, selected_year, selected_month)
    if export_response:
        return export_response
    
    # Import block
    import_errors, import_success = handle_import(
        request,
        selected_year,
        selected_month,
    )

    # Dashboard data
    days = build_days(selected_year, selected_month, days_in_month)
    employees_qs = get_employee_queryset(selected_department, selected_designation)
    record_map = build_record_map(selected_year, selected_month)
    active_shift = get_active_shift()

    dashboard_data = []
    total_bonus_sum = Decimal("0.00")
    total_fine_sum = Decimal("0.00")
    total_final_sum = Decimal("0.00")
    for emp in employees_qs:
        statuses, totals, emp_image_url = build_employee_row(
            emp,
            days,
            today,
            record_map,
            active_shift,
        )
        salary_summary = get_employee_salary_summary(emp, selected_year, selected_month)
        final_salary = salary_summary["base_salary"] + salary_summary["net_adjustment"]
        total_bonus_sum += salary_summary["total_bonus"]
        total_fine_sum += salary_summary["total_fine"]
        total_final_sum += final_salary
        dashboard_data.append(
            {
                "employee_id": emp.employee_id,
                "name": emp.name,
                "designation": emp.designation,
                "statuses": statuses,
                "totals": totals,
                "emp_image_url": emp_image_url,
                "emp_pk": emp.id,
                "final_salary": final_salary,
                "total_bonus": salary_summary["total_bonus"],
                "total_fine": salary_summary["total_fine"],
            }
        )

    departments = Employee.objects.values_list("department", flat=True).distinct()
    designations = Employee.objects.values_list("designation", flat=True).distinct()

    months = list(range(1, 13))
    years = [selected_year - 1, selected_year, selected_year + 1]

    context = {
        "month": selected_month,
        "year": selected_year,
        "days": days,
        "employees": dashboard_data,
        "departments": departments,
        "designations": designations,
        "selected_department": selected_department,
        "selected_designation": selected_designation,
        "months": months,
        "years": years,
        "prev_qs": prev_qs,
        "next_qs": next_qs,
        "import_errors": import_errors,
        "import_success": import_success,
        "has_openpyxl": HAS_OPENPYXL,
    }
    return TemplateResponse(request, "admin/attendance-dashboard.html", context)


@staff_member_required
def attendance_dashboard_pdf(request):
    """
    Export the attendance dashboard grid as a wide PDF with textual statuses.
    """
    from datetime import datetime

    (
        selected_year,
        selected_month,
        selected_department,
        selected_designation,
        today,
        days_in_month,
    ) = get_dashboard_params(request)

    days = build_days(selected_year, selected_month, days_in_month)
    employees_qs = get_employee_queryset(selected_department, selected_designation)
    record_map = build_record_map(selected_year, selected_month)
    active_shift = get_active_shift()

    dashboard_rows = []
    for emp in employees_qs:
        statuses, totals, _ = build_employee_row(
            emp,
            days,
            today,
            record_map,
            active_shift,
        )
        salary_summary = get_employee_salary_summary(emp, selected_year, selected_month)
        final_salary = salary_summary["base_salary"] + salary_summary["net_adjustment"]
        dashboard_rows.append(
            {
                "employee": emp,
                "statuses": statuses,
                "totals": totals,
                "final_salary": final_salary,
                "total_bonus": salary_summary["total_bonus"],
                "total_fine": salary_summary["total_fine"],
            }
        )

    total_bonus_sum = sum(row["total_bonus"] for row in dashboard_rows)
    total_fine_sum = sum(row["total_fine"] for row in dashboard_rows)
    total_final_sum = sum(row["final_salary"] for row in dashboard_rows)

    month_label = datetime(selected_year, selected_month, 1).strftime("%B %Y")
    response = HttpResponse(content_type="application/pdf")
    response[
        "Content-Disposition"
    ] = f'attachment; filename="attendance-dashboard-{selected_year}-{selected_month}.pdf"'

    page_size = landscape(A2)
    pdf = canvas.Canvas(response, pagesize=page_size)
    width, height = page_size
    margin = 30
    y = height - margin

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(margin, y, f"Attendance Dashboard - {month_label}")
    y -= 18
    pdf.setFont("Helvetica", 10)
    if selected_department:
        pdf.drawString(margin, y, f"Department: {selected_department}")
        y -= 12
    if selected_designation:
        pdf.drawString(margin, y, f"Designation: {selected_designation}")
        y -= 12
    y -= 4

    legend_entries = [
        f"{abbr} = {name}" for name, abbr in STATUS_LABEL_MAP.items()
    ]
    pdf.setFont("Helvetica", 8)
    pdf.drawString(margin, y, "Legend: " + " | ".join(legend_entries))
    y -= 10
    pdf.drawString(margin, y, "(! indicates the employee arrived late on that day)")
    y -= 14

    name_col = margin
    designation_col = margin + 160
    day_width = 18
    day_start = margin + 280
    totals_start = day_start + len(days) * day_width + 15
    totals_headers = [
        "P",
        "L",
        "OL",
        "H",
        "A",
        "HD",
        "EL",
        "BON",
        "FIN",
        "FS",
    ]
    totals_positions = []
    x_pos = totals_start
    for label in totals_headers:
        totals_positions.append((label, x_pos))
        x_pos += 60

    def draw_headers():
        nonlocal y
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(name_col, y, "Employee (ID)")
        pdf.drawString(designation_col, y, "Designation")
        pdf.setFont("Helvetica-Bold", 7)
        for idx, day in enumerate(days):
            pdf.drawString(day_start + idx * day_width, y, str(day["num"]))
        pdf.setFont("Helvetica-Bold", 8)
        for label, xpos in totals_positions:
            pdf.drawString(xpos, y, label)
        y -= 12
        pdf.line(margin, y, width - margin, y)
        y -= 8

    def ensure_space():
        nonlocal y
        if y <= margin + 40:
            pdf.showPage()
            y = height - margin
            draw_headers()

    draw_headers()
    pdf.setFont("Helvetica", 8)
    for row in dashboard_rows:
        ensure_space()
        employee_label = f"{row['employee'].name} ({row['employee'].employee_id})"
        pdf.drawString(name_col, y, employee_label[:40])
        pdf.drawString(
            designation_col,
            y,
            (row["employee"].designation or "-")[:18],
        )
        pdf.setFont("Helvetica", 6)
        for idx, status_entry in enumerate(row["statuses"]):
            label = _status_to_label(status_entry)
            xpos = day_start + idx * day_width
            if label.endswith("!"):
                pdf.setFillColorRGB(0, 0, 0)
                pdf.drawString(xpos, y, label[:-1])
                pdf.setFillColorRGB(0.8, 0.0, 0.0)
                pdf.drawString(xpos + 10, y + 4, "!")
                pdf.setFillColorRGB(0, 0, 0)
            else:
                pdf.drawString(xpos, y, label)
        pdf.setFont("Helvetica", 8)
        pdf.drawString(totals_positions[0][1], y, str(row["totals"]["Present"]))
        pdf.drawString(totals_positions[1][1], y, str(row["totals"]["Late"]))
        pdf.drawString(totals_positions[2][1], y, str(row["totals"]["On_Leave"]))
        pdf.drawString(totals_positions[3][1], y, str(row["totals"]["Holiday"]))
        pdf.drawString(totals_positions[4][1], y, str(row["totals"]["Absent"]))
        pdf.drawString(totals_positions[5][1], y, str(row["totals"]["Half_Day"]))
        pdf.drawString(totals_positions[6][1], y, str(row["totals"]["Early_Leave"]))
        pdf.drawRightString(
            totals_positions[7][1] + 50, y, f"{row['total_bonus']:.2f}"
        )
        pdf.drawRightString(
            totals_positions[8][1] + 50, y, f"{row['total_fine']:.2f}"
        )
        pdf.drawRightString(
            totals_positions[9][1] + 50, y, f"{row['final_salary']:.2f}"
        )
        y -= 14

    ensure_space()
    pdf.setFont("Helvetica-Bold", 8)
    pdf.line(margin, y, width - margin, y)
    y -= 14
    pdf.drawString(margin, y, "TOTALS")
    pdf.drawString(totals_positions[0][1], y, str(sum(r["totals"]["Present"] for r in dashboard_rows)))
    pdf.drawString(totals_positions[1][1], y, str(sum(r["totals"]["Late"] for r in dashboard_rows)))
    pdf.drawString(totals_positions[2][1], y, str(sum(r["totals"]["On_Leave"] for r in dashboard_rows)))
    pdf.drawString(totals_positions[3][1], y, str(sum(r["totals"]["Holiday"] for r in dashboard_rows)))
    pdf.drawString(totals_positions[4][1], y, str(sum(r["totals"]["Absent"] for r in dashboard_rows)))
    pdf.drawString(totals_positions[5][1], y, str(sum(r["totals"]["Half_Day"] for r in dashboard_rows)))
    pdf.drawString(totals_positions[6][1], y, str(sum(r["totals"]["Early_Leave"] for r in dashboard_rows)))
    pdf.drawRightString(totals_positions[7][1] + 50, y, f"{total_bonus_sum:.2f}")
    pdf.drawRightString(totals_positions[8][1] + 50, y, f"{total_fine_sum:.2f}")
    pdf.drawRightString(totals_positions[9][1] + 50, y, f"{total_final_sum:.2f}")

    pdf.showPage()
    pdf.save()
    return response



def _image_to_base64(image_field):
    if not image_field:
        return None
    try:
        with image_field.open('rb') as image_fp:
            return base64.b64encode(image_fp.read()).decode('ascii')
    except Exception:
        return None


def _serialize_employee(employee):
    return {
        "employee_id": employee.employee_id,
        "name": employee.name,
        "facial_template": employee.facial_template or "",
        "face_image": _image_to_base64(employee.employee_image),
    }


def _save_employee_photo(employee, image_file):
    if not image_file:
        return
    try:
        image_file.seek(0)
    except Exception:
        pass
    filename = image_file.name or f"{employee.employee_id}_{timezone.now().strftime('%Y%m%d%H%M%S')}.jpg"
    employee.employee_image.save(filename, ContentFile(image_file.read()), save=False)


def _assign_attendance_image(record, field_name, image_file):
    if not image_file:
        return
    try:
        image_file.seek(0)
    except Exception:
        pass
    data = image_file.read()
    if not data:
        return
    filename = f"{field_name}_{record.employee.employee_id}_{timezone.now().strftime('%Y%m%d%H%M%S')}.jpg"
    getattr(record, field_name).save(filename, ContentFile(data), save=False)


def _generate_employee_id():
    while True:
        candidate = f"TMP{get_random_string(6).upper()}"
        if not Employee.objects.filter(employee_id=candidate).exists():
            return candidate


def _json_error(message, status=400):
    return JsonResponse({"detail": message}, status=status)


@csrf_exempt
def employees_sync_api(request):
    if request.method != 'GET':
        return _json_error('Method not allowed', status=405)

    employees = Employee.objects.filter(is_active=True).order_by('name')
    payload = [_serialize_employee(emp) for emp in employees]
    return JsonResponse({"employees": payload})


@staff_member_required
def push_employee_sync(request):
    """
    Trigger a push notification so enrolled APKs refresh their local database.
    """
    if request.method == "POST":
        tokens = DeviceRegistration.objects.values_list("token", flat=True)
        success, detail = send_database_update_notification(tokens)
        if success:
            messages.success(request, detail)
        else:
            if "No registered devices" in detail:
                messages.warning(request, detail)
            else:
                messages.error(request, detail)
    else:
        messages.error(request, "Unsupported request method.")
    return redirect("admin:attendance_employee_changelist")


@csrf_exempt
def enroll_employee_api(request):
    if request.method != 'POST':
        return _json_error('Method not allowed', status=405)

    employee_id = (request.POST.get('employee_id') or '').strip()
    name = (request.POST.get('name') or '').strip()
    template = (request.POST.get('template') or '').strip()

    if not employee_id or not name or not template:
        return _json_error('employee_id, name, and template are required.')

    employee, created = Employee.objects.get_or_create(
        employee_id=employee_id,
        defaults={'name': name}
    )
    employee.name = name
    employee.facial_template = template
    employee.is_active = True

    image_file = request.FILES.get('image')
    if image_file:
        _save_employee_photo(employee, image_file)

    employee.save()

    message = 'Employee enrolled' if created else 'Employee updated'
    return JsonResponse({
        "status": "ok",
        "employee_id": employee.employee_id,
        "name": employee.name,
        "message": message,
    })


@csrf_exempt
def enroll_unknown_employee_api(request):
    if request.method != 'POST':
        return _json_error('Method not allowed', status=405)

    template = (request.POST.get('template') or '').strip()
    image_file = request.FILES.get('image')

    if not template:
        return _json_error('Template is required for unknown enrollment.')
    if not image_file:
        return _json_error('Image file is required for unknown enrollment.')

    employee_id = _generate_employee_id()
    name = f"Pending Employee {employee_id}"
    employee = Employee.objects.create(
        employee_id=employee_id,
        name=name,
        facial_template=template,
        is_active=True,
    )
    _save_employee_photo(employee, image_file)
    employee.save()

    return JsonResponse({
        "status": "ok",
        "employee_id": employee.employee_id,
        "name": employee.name,
        "message": "Unknown employee captured",
    })


@csrf_exempt
def attendance_event_api(request):
    if request.method != 'POST':
        return _json_error('Method not allowed', status=405)

    employee_id = (request.POST.get('employee_id') or '').strip()
    image_file = request.FILES.get('image')
    device_id = (request.POST.get('device_id') or '').strip()

    if not employee_id:
        return _json_error('employee_id is required.')
    if not image_file:
        return _json_error('Image file is required.')

    try:
        employee = Employee.objects.get(employee_id=employee_id)
    except Employee.DoesNotExist:
        return _json_error('Employee not found.', status=404)

    now = dhaka_now()
    record, _ = AttendanceRecord.objects.get_or_create(
        employee=employee,
        date=now.date(),
    )

    message = ''
    check_type = ''

    if record.checkin_time is None:
        record.checkin_time = now
        _assign_attendance_image(record, 'checkin_image', image_file)
        check_type = 'IN'
        message = f"Welcome {employee.name}"
    elif record.checkout_time is None:
        time_since_checkin = now - record.checkin_time if record.checkin_time else None
        if time_since_checkin and time_since_checkin < ATTENDANCE_COOLDOWN:
            remaining = ATTENDANCE_COOLDOWN - time_since_checkin
            minutes = math.ceil(remaining.total_seconds() / 60)
            message = f"Please wait {minutes} more minute(s) before checkout."
            return JsonResponse({
                "status": "wait",
                "employee_id": employee.employee_id,
                "employee_name": employee.name,
                "check_type": "WAIT",
                "message": message,
                "wait_minutes": minutes,
            })
        record.checkout_time = now
        _assign_attendance_image(record, 'checkout_image', image_file)
        check_type = 'OUT'
        message = f"Goodbye {employee.name}"
    else:
        check_type = 'NONE'
        message = f"Attendance already completed today for {employee.name}."

    if device_id:
        record.device_id = device_id

    record.save()

    return JsonResponse({
        "status": "ok",
        "employee_id": employee.employee_id,
        "employee_name": employee.name,
        "check_type": check_type,
        "message": message,
    })


@csrf_exempt
def register_token_api(request):
    if request.method != 'POST':
        return _json_error('Method not allowed', status=405)

    token = (request.POST.get('token') or '').strip()
    platform = (request.POST.get('platform') or '').strip()

    if not token and request.body:
        try:
            payload = json.loads(request.body.decode('utf-8'))
            token = (payload.get('token') or '').strip()
            platform = (payload.get('platform') or platform).strip()
        except Exception:
            pass

    if not token:
        return _json_error('Token is required.')

    DeviceRegistration.objects.update_or_create(
        token=token,
        defaults={'platform': platform},
    )

    return JsonResponse({"status": "ok"})

@staff_member_required
def salary_management_view(request):
    """
    Comprehensive salary management interface.
    
    Features:
    - Monthly salary calculations with automatic adjustments
    - Manual bonus/fine management
    - Bulk processing of automatic adjustments
    - Employee-wise salary breakdown
    - Real-time calculation based on attendance
    
    Automatic Rules:
    - Fine: 3+ late days = 1 day salary fine per 3 days
    - Bonus: 100% Present + No late days = 1000 BDT bonus
    """
    from datetime import datetime

    selected_month = int(request.GET.get("month", datetime.now().month))
    selected_year = int(request.GET.get("year", datetime.now().year))

    # Process automatic adjustments if requested
    if request.method == "POST" and request.POST.get("process_auto"):
        processed_count = process_monthly_salary_adjustments(
            selected_year, selected_month
        )
        context = {
            "message": f"Processed {processed_count} automatic salary adjustments",
            "message_type": "success",
        }
    else:
        context = {}

    # Get all employees with salary summaries
    employees_data = []
    for emp in Employee.objects.all():
        summary = get_employee_salary_summary(emp, selected_year, selected_month)
        employees_data.append({"employee": emp, "summary": summary})

    context.update(
        {
            "month": selected_month,
            "year": selected_year,
            "employees_data": employees_data,
            "months": list(range(1, 13)),
            "years": [selected_year - 1, selected_year, selected_year + 1],
        }
    )

    return TemplateResponse(request, "admin/salary-management.html", context)


@staff_member_required
def salary_report_view(request):
    """
    Detailed salary report with comprehensive breakdown.
    
    Features:
    - Monthly salary calculations per employee
    - Department-wise filtering
    - Total salary summaries
    - Bonus/fine details with reasons
    - Working days and late days tracking
    - Export-ready format for payroll processing
    """
    from datetime import datetime

    selected_month = int(request.GET.get("month", datetime.now().month))
    selected_year = int(request.GET.get("year", datetime.now().year))
    selected_department = request.GET.get("department") or None
    
    # Process automatic adjustments if requested
    message = None
    if request.method == "POST" and request.POST.get("process_auto"):
        processed_count = process_monthly_salary_adjustments(selected_year, selected_month)
        message = f"Processed {processed_count} automatic salary adjustments for {datetime(selected_year, selected_month, 1).strftime('%B %Y')}"

    # Filter employees by department if selected
    employees_qs = Employee.objects.all()
    if selected_department:
        employees_qs = employees_qs.filter(department=selected_department)

    salary_data, totals = _build_salary_report_data(
        selected_year, selected_month, selected_department
    )

    departments = Employee.objects.values_list("department", flat=True).distinct()

    context = {
        "month": selected_month,
        "year": selected_year,
        "selected_department": selected_department,
        "salary_data": salary_data,
        "departments": departments,
        "months": list(range(1, 13)),
        "years": [selected_year - 1, selected_year, selected_year + 1],
        "totals": totals,
        "month_name": datetime(selected_year, selected_month, 1).strftime("%B %Y"),
        "message": message,
    }

    return TemplateResponse(request, "admin/salary-report-new.html", context)


@staff_member_required
def salary_report_pdf(request):
    from datetime import datetime

    selected_month = int(request.GET.get("month", datetime.now().month))
    selected_year = int(request.GET.get("year", datetime.now().year))
    selected_department = request.GET.get("department") or None

    salary_data, totals = _build_salary_report_data(
        selected_year, selected_month, selected_department
    )

    month_label = datetime(selected_year, selected_month, 1).strftime("%B %Y")
    response = HttpResponse(content_type="application/pdf")
    response[
        "Content-Disposition"
    ] = f'attachment; filename="salary-report-{selected_year}-{selected_month}.pdf"'

    page_size = landscape(A3)
    pdf = canvas.Canvas(response, pagesize=page_size)
    width, height = page_size
    margin = 40
    y = height - margin

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(margin, y, f"Salary Report - {month_label}")
    y -= 20
    if selected_department:
        pdf.setFont("Helvetica", 12)
        pdf.drawString(margin, y, f"Department: {selected_department}")
        y -= 15
    pdf.setFont("Helvetica", 10)
    y -= 10

    columns = [
        ("Employee", margin, 220, "left"),
        ("Department", margin + 230, 110, "left"),
        ("Working", margin + 360, 40, "left"),
        ("Late", margin + 410, 40, "left"),
        ("Base", margin + 460, 70, "right"),
        ("Bonus", margin + 540, 70, "right"),
        ("Fines", margin + 620, 70, "right"),
        ("Final", margin + 700, 90, "right"),
    ]

    def draw_headers():
        nonlocal y
        pdf.setFont("Helvetica-Bold", 10)
        for label, xpos, _, align in columns:
            if align == "right":
                pdf.drawRightString(xpos + 60, y, label)
            else:
                pdf.drawString(xpos, y, label)
        y -= 14
        pdf.line(margin, y, width - margin, y)
        y -= 8
        pdf.setFont("Helvetica", 9)

    draw_headers()

    def ensure_space():
        nonlocal y
        if y <= margin:
            pdf.showPage()
            y = height - margin
            draw_headers()

    for data in salary_data:
        ensure_space()
        employee_label = f"{data['employee'].name} ({data['employee'].employee_id})"
        pdf.drawString(columns[0][1], y, employee_label[:30])
        pdf.drawString(columns[1][1], y, (data["employee"].department or "-")[:18])
        pdf.drawString(columns[2][1], y, str(data["working_days"]))
        pdf.drawString(columns[3][1], y, str(data["late_days"]))
        pdf.drawRightString(columns[4][1] + columns[4][2], y, f"{data['base_salary']:.2f}")
        pdf.drawRightString(columns[5][1] + columns[5][2], y, f"{data['total_bonus']:.2f}")
        pdf.drawRightString(columns[6][1] + columns[6][2], y, f"{data['total_fine']:.2f}")
        pdf.drawRightString(columns[7][1] + columns[7][2], y, f"{data['final_salary']:.2f}")
        y -= 14

    ensure_space()
    pdf.setFont("Helvetica-Bold", 10)
    pdf.line(margin, y, width - margin, y)
    y -= 14
    pdf.drawString(margin, y, "TOTALS")
    pdf.drawRightString(columns[4][1] + columns[4][2], y, f"{totals['base_salary']:.2f}")
    pdf.drawRightString(columns[5][1] + columns[5][2], y, f"{totals['bonuses']:.2f}")
    pdf.drawRightString(columns[6][1] + columns[6][2], y, f"{totals['fines']:.2f}")
    pdf.drawRightString(columns[7][1] + columns[7][2], y, f"{totals['final_salary']:.2f}")
    y -= 20
    pdf.setFont("Helvetica-Oblique", 9)
    pdf.drawString(
        margin,
        y,
        "Final Salary column reflects all bonuses and deductions per employee.",
    )

    pdf.showPage()
    pdf.save()
    return response


def _build_salary_report_data(selected_year, selected_month, selected_department=None):
    salary_data = []
    total_base_salary = Decimal("0.00")
    total_bonuses = Decimal("0.00")
    total_fines = Decimal("0.00")
    total_final_salary = Decimal("0.00")
    employees_qs = Employee.objects.all()
    if selected_department:
        employees_qs = employees_qs.filter(department=selected_department)

    for emp in employees_qs:
        summary = get_employee_salary_summary(emp, selected_year, selected_month)

        final_salary = summary["base_salary"] + summary["net_adjustment"]

        salary_data.append(
            {
                "employee": emp,
                "base_salary": summary["base_salary"],
                "total_bonus": summary["total_bonus"],
                "total_fine": summary["total_fine"],
                "final_salary": final_salary,
                "late_days": summary["late_days"],
                "working_days": summary["working_days"],
                "bonuses": summary["bonuses"],
                "fines": summary["fines"],
            }
        )

        # Add to totals
        total_base_salary += summary["base_salary"]
        total_bonuses += summary["total_bonus"]
        total_fines += summary["total_fine"]
        total_final_salary += final_salary

    totals = {
        "base_salary": total_base_salary,
        "bonuses": total_bonuses,
        "fines": total_fines,
        "final_salary": total_final_salary,
    }
    return salary_data, totals


STATUS_LABEL_MAP = {
    "Present": "P",
    "Absent": "A",
    "Early Leave": "EL",
    "Half Day": "HD",
    "On Leave": "OL",
    "Holiday": "H",
    "Pending": "PD",
    "Off Day": "OFF",
    "Not Joined": "NJ",
}


def _status_to_label(status_entry):
    status = status_entry.get("status")
    if not status:
        return ""
    label = STATUS_LABEL_MAP.get(status, status[:3].upper())
    if status_entry.get("is_late"):
        label = f"{label}!"
    return label


@staff_member_required
def employee_detail_view(request, employee_id):
    """
    Employee detail view with attendance summary and recent records.
    
    Features:
    - Employee information and photo
    - Monthly attendance summary
    - Recent attendance records
    - Quick actions (add attendance, edit employee)
    """
    from django.shortcuts import get_object_or_404
    from datetime import datetime, timedelta
    
    employee = get_object_or_404(Employee, id=employee_id)
    
    # Get current month attendance summary
    now = datetime.now()
    current_month_records = AttendanceRecord.objects.filter(
        employee=employee,
        date__year=now.year,
        date__month=now.month
    ).order_by('-date')
    
    # Calculate monthly stats
    monthly_stats = {
        'present': current_month_records.filter(status='Present').count(),
        'absent': current_month_records.filter(status='Absent').count(),
        'late': sum(1 for r in current_month_records if r.is_late_indicator()),
        'on_leave': current_month_records.filter(status='On Leave').count(),
        'holiday': current_month_records.filter(status='Holiday').count(),
    }
    
    # Get recent 10 records
    recent_records = AttendanceRecord.objects.filter(
        employee=employee
    ).order_by('-date')[:10]
    
    context = {
        'employee': employee,
        'monthly_stats': monthly_stats,
        'recent_records': recent_records,
        'current_month': now.strftime('%B %Y'),
    }
    
    return TemplateResponse(request, "admin/employee-detail.html", context)


@staff_member_required
def holiday_management_view(request):
    """
    Advanced holiday management system.
    
    Features:
    - Bulk holiday creation with scope targeting
    - Government holiday auto-generation for Bangladesh
    - Department/designation/custom employee selection
    - Real-time holiday activation/deactivation
    - Smart processing (preserves existing attendance)
    - Holiday calendar management
    
    Supported Operations:
    - Create custom holidays
    - Generate government holidays
    - Update existing holidays
    - Delete holidays with cleanup
    """
    from datetime import datetime, date
    
    message = None
    message_type = None
    
    if request.method == "POST":
        if request.POST.get("create_holiday"):
            try:
                name = request.POST.get("name")
                start_date = datetime.strptime(request.POST.get("start_date"), "%Y-%m-%d").date()
                end_date = datetime.strptime(request.POST.get("end_date"), "%Y-%m-%d").date()
                scope = request.POST.get("scope")
                description = request.POST.get("description", "")
                is_government = request.POST.get("is_government") == "1"
                
                holiday = BulkHoliday.objects.create(
                    name=name,
                    start_date=start_date,
                    end_date=end_date,
                    scope=scope,
                    description=description,
                    created_by=request.user.username if not is_government else "System",
                    is_government=is_government,
                    is_active=True
                )
                
                if scope == "department":
                    holiday.department = request.POST.get("department")
                elif scope == "designation":
                    holiday.designation = request.POST.get("designation")
                elif scope == "custom":
                    employee_ids = request.POST.getlist("selected_employees")
                    holiday.selected_employees.set(employee_ids)
                
                holiday.save()
                message = f"Holiday '{name}' created and activated!"
                message_type = "success"
                
            except Exception as e:
                message = f"Error: {str(e)}"
                message_type = "error"
        
        elif request.POST.get("update_holiday"):
            holiday_id = request.POST.get("holiday_id")
            try:
                holiday = BulkHoliday.objects.get(id=holiday_id)
                holiday.name = request.POST.get("name")
                holiday.start_date = datetime.strptime(request.POST.get("start_date"), "%Y-%m-%d").date()
                holiday.end_date = datetime.strptime(request.POST.get("end_date"), "%Y-%m-%d").date()
                holiday.is_active = request.POST.get("is_active") == "1"
                holiday.save()
                message = f"Holiday '{holiday.name}' updated!"
                message_type = "success"
            except BulkHoliday.DoesNotExist:
                message = "Holiday not found"
                message_type = "error"
            except Exception as e:
                message = f"Error: {str(e)}"
                message_type = "error"
        
        elif request.POST.get("delete_holiday"):
            holiday_id = request.POST.get("holiday_id")
            try:
                holiday = BulkHoliday.objects.get(id=holiday_id)
                name = holiday.name
                holiday.delete()
                message = f"Holiday '{name}' deleted!"
                message_type = "success"
            except BulkHoliday.DoesNotExist:
                message = "Holiday not found"
                message_type = "error"
            except Exception as e:
                message = f"Error: {str(e)}"
                message_type = "error"
        
        elif request.POST.get("auto_generate_holidays"):
            year = int(request.POST.get("generate_year", datetime.now().year))
            try:
                holidays = [
                    {"name": "International Mother Language Day", "month": 2, "day": 21},
                    {"name": "Independence Day", "month": 3, "day": 26},
                    {"name": "Bengali New Year", "month": 4, "day": 14},
                    {"name": "May Day", "month": 5, "day": 1},
                    {"name": "National Mourning Day", "month": 8, "day": 15},
                    {"name": "Victory Day", "month": 12, "day": 16},
                    {"name": "Christmas Day", "month": 12, "day": 25},
                ]
                
                created_count = 0
                for holiday_data in holidays:
                    holiday_date = date(year, holiday_data["month"], holiday_data["day"])
                    holiday_name = f"{holiday_data['name']} {year}"
                    
                    if not BulkHoliday.objects.filter(name=holiday_name, start_date=holiday_date).exists():
                        BulkHoliday.objects.create(
                            name=holiday_name,
                            start_date=holiday_date,
                            end_date=holiday_date,
                            scope='all',
                            description="Bangladesh Government Holiday",
                            created_by="System",
                            is_government=True,
                            is_active=True
                        )
                        created_count += 1
                
                message = f"Generated {created_count} government holidays for {year}!"
                message_type = "success"
                
            except Exception as e:
                message = f"Error: {str(e)}"
                message_type = "error"
    
    all_holidays = BulkHoliday.objects.all().order_by('-created_at')
    government_holidays = all_holidays.filter(is_government=True)
    custom_holidays = all_holidays.filter(is_government=False)
    
    departments = Employee.objects.values_list("department", flat=True).distinct()
    designations = Employee.objects.values_list("designation", flat=True).distinct()
    employees = Employee.objects.all().order_by('name')
    
    context = {
        "holidays": custom_holidays,
        "government_holidays": government_holidays,
        "departments": departments,
        "designations": designations,
        "employees": employees,
        "message": message,
        "message_type": message_type,
        "current_user": request.user.username,
        "current_year": datetime.now().year,
    }
    
    return TemplateResponse(request, "admin/holiday-management.html", context)
















