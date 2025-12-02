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
from django.db.models import Q
from io import BytesIO
import base64
import json
import math
from datetime import timedelta
import zipfile

# Local app imports
from .models import (
    Employee,
    AttendanceRecord,
    DeviceRegistration,
    get_active_shift,
    BulkHoliday,
    dhaka,
    dhaka_now,
    SalaryStatistic,
    CompanyInfo,
    ModeratorLabel,
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
from .utils.moderator_labels import get_label as get_moderator_label, DEFAULT_LABELS
from .utils.import_helpers import handle_import, handle_export, HAS_OPENPYXL
from .utils.push_helpers import send_database_update_notification
from .utils.push_helpers import send_database_update_notification

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
    for emp in employees_qs:
        statuses, totals, emp_image_url = build_employee_row(
            emp,
            days,
            today,
            record_map,
            active_shift,
        )
        dashboard_data.append(
            {
                "employee_id": emp.employee_id,
                "name": emp.name,
                "designation": emp.designation,
                "statuses": statuses,
                "totals": totals,
                "emp_image_url": emp_image_url,
                "emp_pk": emp.id,
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
    from django.shortcuts import get_object_or_404
    (
        selected_year,
        selected_month,
        selected_department,
        selected_designation,
        today,
        days_in_month,
    ) = get_dashboard_params(request)

    # Optional: allow downloading for a single employee via ?employee_id=<pk>
    single_employee_id = request.GET.get("employee_id")
    try:
        single_employee_id = int(single_employee_id) if single_employee_id else None
    except (TypeError, ValueError):
        single_employee_id = None

    employees_qs = get_employee_queryset(selected_department, selected_designation)
    if single_employee_id:
        employees_qs = employees_qs.filter(id=single_employee_id)
        if not employees_qs.exists():
            get_object_or_404(Employee, id=single_employee_id)  # raise 404 if invalid

    pdf_bytes, filename = _render_attendance_pdf(
        selected_year,
        selected_month,
        selected_department,
        selected_designation,
        today,
        days_in_month,
        employees_qs,
        single_employee_id=single_employee_id,
        theme=request.GET.get("theme", "light"),
    )
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.write(pdf_bytes)
    return response


@staff_member_required
def attendance_dashboard_pdf_bulk(request):
    """
    Download individual PDFs (one per employee) for the filtered set as a ZIP.
    """
    (
        selected_year,
        selected_month,
        selected_department,
        selected_designation,
        today,
        days_in_month,
    ) = get_dashboard_params(request)

    employees_qs = get_employee_queryset(selected_department, selected_designation)
    search_term = (request.GET.get("search") or "").strip()
    if search_term:
        employees_qs = employees_qs.filter(
            Q(name__icontains=search_term)
            | Q(employee_id__icontains=search_term)
            | Q(designation__icontains=search_term)
        )
    theme = (request.GET.get("theme") or "").lower()
    if not employees_qs.exists():
        return HttpResponse("No employees found for the current filters.", status=404)

    record_map = build_record_map(selected_year, selected_month)
    active_shift = get_active_shift()

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for emp in employees_qs:
            pdf_bytes, filename = _render_attendance_pdf(
                selected_year,
                selected_month,
                selected_department,
                selected_designation,
                today,
                days_in_month,
                employees_qs.filter(id=emp.id),
                single_employee_id=emp.id,
                record_map=record_map,
                active_shift=active_shift,
                theme=theme,
            )
            zip_file.writestr(filename, pdf_bytes)

    response = HttpResponse(zip_buffer.getvalue(), content_type="application/zip")
    response["Content-Disposition"] = (
        f'attachment; filename="attendance-individual-pdfs-{selected_year}-{selected_month}.zip"'
    )
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
    


    # Filter employees by department if selected
    employees_qs = Employee.objects.all()
    if selected_department:
        employees_qs = employees_qs.filter(department=selected_department)

    import calendar
    days_in_month = calendar.monthrange(selected_year, selected_month)[1]
    stats = _ensure_salary_statistics(selected_year, selected_month, employees_qs, days_in_month)
    departments = Employee.objects.values_list("department", flat=True).distinct()

    # Calculate totals for the report
    totals = {
        "basic_salary": sum(s["basic_salary"] or 0 for s in stats),
        "house_rent": sum(s["house_rent"] or 0 for s in stats),
        "medical_allowance": sum(s["medical_allowance"] or 0 for s in stats),
        "conveyance_allowance": sum(s["conveyance_allowance"] or 0 for s in stats),
        "food_allowance": sum(s["food_allowance"] or 0 for s in stats),
        "other_allowance": sum(s["other_allowance"] or 0 for s in stats),
        "gross_salary": sum(s["gross_salary"] or 0 for s in stats),
        "working_days": sum(s["working_days"] or 0 for s in stats),
        "weekends": sum(s["weekends"] or 0 for s in stats),
        "leave_days": sum(s["leave_days"] or 0 for s in stats),
        "holidays": sum(s["holidays"] or 0 for s in stats),
        "attended_days": sum(s["attended_days"] or 0 for s in stats),
        "late_days": sum(s.get("late_days", 0) for s in stats),
        "ot_hours": sum(s["ot_hours"] or 0 for s in stats),
        "ot_rate": sum(s["ot_rate"] or 0 for s in stats),
        "ot_amount": sum(s["ot_amount"] or 0 for s in stats),
        "hd_allowance": sum(s["hd_allowance"] or 0 for s in stats),
        "attendance_bonus": sum(s["attendance_bonus"] or 0 for s in stats),
        "other_deduction": sum(s["other_deduction"] or 0 for s in stats),
        "late_fine": sum(s["late_fine"] or 0 for s in stats),
        "tds_amount": sum(s["tds_amount"] or 0 for s in stats),
        "payable": sum(s["payable"] or 0 for s in stats),
    }

    context = {
        "month": selected_month,
        "year": selected_year,
        "selected_department": selected_department,
        "salary_data": stats,
        "departments": departments,
        "months": list(range(1, 13)),
        "years": [selected_year - 1, selected_year, selected_year + 1],\
        "totals": totals,
        "month_name": datetime(selected_year, selected_month, 1).strftime("%B %Y"),
    }

    return TemplateResponse(request, "admin/salary-report-new.html", context)


@staff_member_required
def salary_report_pdf(request):
    from datetime import datetime

    selected_month = int(request.GET.get("month", datetime.now().month))
    selected_year = int(request.GET.get("year", datetime.now().year))
    selected_department = request.GET.get("department") or None
    employee_id = request.GET.get("employee_id")
    employees_qs = Employee.objects.all()
    if selected_department:
        employees_qs = employees_qs.filter(department=selected_department)
    if employee_id:
        employees_qs = employees_qs.filter(id=employee_id)

    import calendar
    days_in_month = calendar.monthrange(selected_year, selected_month)[1]
    stats = _ensure_salary_statistics(selected_year, selected_month, employees_qs, days_in_month)
    month_label = datetime(selected_year, selected_month, 1).strftime("%B %Y")
    response = HttpResponse(content_type="application/pdf")
    response[
        "Content-Disposition"
    ] = f'attachment; filename="salary-report-{selected_year}-{selected_month}.pdf"'

    from reportlab.lib.pagesizes import legal
    page_size = landscape(legal)
    pdf = canvas.Canvas(response, pagesize=page_size)
    width, height = page_size
    margin = 20
    y = height - margin

    # Use the attendance/dashboard palette (light base, green header, red subheader, blue totals)
    theme = (request.GET.get("theme") or "light").lower()
    page_bg = (1, 1, 1)
    header_fill = (0.12, 0.55, 0.32)   # green header
    subheader_fill = (0.72, 0.16, 0.28) # red subheader
    row_fill_primary = (0.98, 0.99, 0.97)
    row_fill_secondary = (0.94, 0.97, 0.92)
    totals_fill = (0.16, 0.36, 0.60)    # deep blue footer
    grid_color = (0.70, 0.78, 0.74)
    title_color = (1, 1, 1)
    text_color = (0.12, 0.20, 0.24)

    # Draw Page Background
    pdf.setFillColorRGB(*page_bg)
    pdf.rect(0, 0, width, height, stroke=0, fill=1)

    header_height = 90
    pdf.setFillColorRGB(*header_fill)
    pdf.rect(0, height - header_height, width, header_height, stroke=0, fill=1)
    
    # Draw Company Info
    company = CompanyInfo.get_solo()
    pdf.setFillColorRGB(1, 1, 1)

    # Logo (left), text centered
    if company.logo:
        try:
            pdf.drawImage(company.logo.path, margin, height - 70, width=60, height=60, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

    center_x = width / 2
    pdf.setFont("Helvetica-Bold", 18)
    # Keep the name safely inside the banner
    name_y = height - header_height + 70
    pdf.drawCentredString(center_x, name_y, company.name)

    pdf.setFont("Helvetica", 10)
    y_offset = name_y - 18
    if company.address:
        pdf.drawCentredString(center_x, y_offset, company.address)
        y_offset -= 12
    if company.email:
        pdf.drawCentredString(center_x, y_offset, f"Email: {company.email}")
        y_offset -= 12
    if company.phone:
        pdf.drawCentredString(center_x, y_offset, f"Phone: {company.phone}")
        y_offset -= 12
    if company.tin:
        pdf.drawCentredString(center_x, y_offset, f"TIN: {company.tin}")
        y_offset -= 12
    if company.bin:
        pdf.drawCentredString(center_x, y_offset, f"BIN/BFN: {company.bin}")
        y_offset -= 12
    if company.founder:
        pdf.drawCentredString(center_x, y_offset, f"Founder: {company.founder}")

    report_title = get_moderator_label("salary_report_title", "Salary Report")
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(width - margin - 250, height - header_height + 20, f"{report_title} - {month_label}")
    y = height - header_height - 10  # start table just below banner
    pdf.setFillColorRGB(*text_color)
    pdf.setFont("Helvetica", 9)
    if selected_department:
        pdf.drawString(margin, y, f"Department: {selected_department}")
        y -= 12
    if employee_id:
        pdf.drawString(margin, y, f"Employee filter: {employee_id}")
        y -= 12
    y -= 6


    # Define columns (Header, Alignment)
    headers = [
        ("S/N", "center"),
        (f"{get_moderator_label('salary_employee_header', 'Name')}\n(ID)", "left"),
        (get_moderator_label("salary_joining_header", "Join\nDate"), "left"),
        (get_moderator_label("salary_bank_header", "Bank"), "left"),
        (get_moderator_label("salary_basic_header", "Basic"), "right"),
        (get_moderator_label("salary_house_rent_header", "House\nRent"), "right"),
        (get_moderator_label("salary_medical_header", "Med"), "right"),
        (get_moderator_label("salary_conveyance_header", "Conv"), "right"),
        (get_moderator_label("salary_food_header", "Food"), "right"),
        (get_moderator_label("salary_other_header", "Other\nAllow"), "right"),
        (get_moderator_label("salary_gross_header", "Gross"), "right"),
        ("WD", "center"),
        ("WKN", "center"),
        ("L", "center"),
        ("H", "center"),
        ("Att\nDay", "center"),
        ("Late", "center"),
        ("OT\nTime", "right"),
        ("OT\nRate", "right"),
        ("OT\nAmt", "right"),
        ("HD\nAllow", "right"),
        ("Att\nBonus", "right"),
        ("Other\nDeduct", "right"),
        ("Fine", "right"),
        ("TDS", "center"),
        ("Payable", "right"),
        ("Signature", "center"),
    ]

    # Initialize widths and totals
    col_widths = [0] * len(headers)
    padding = 6
    
    # Measure headers
    for i, (label, _) in enumerate(headers):
        lines = label.split('\n')
        w = 0
        for line in lines:
            w = max(w, pdf.stringWidth(line, "Helvetica-Bold", 8))
        col_widths[i] = max(col_widths[i], w + padding)

    totals_acc = {
        "basic": Decimal("0"),
        "house_rent": Decimal("0"),
        "medical": Decimal("0"),
        "conv": Decimal("0"),
        "food": Decimal("0"),
        "other": Decimal("0"),
        "gross": Decimal("0"),
        "wd": 0,
        "wkn": 0,
        "l": 0,
        "h": 0,
        "att": 0,
        "late": 0, # Added
        "ot_hours": Decimal("0"),
        "ot_rate": Decimal("0"),
        "ot_amt": Decimal("0"),
        "hd_allow": Decimal("0"),
        "att_bonus": Decimal("0"),
        "other_deduct": Decimal("0"),
        "late_fine": Decimal("0"), # Added
        "tds_amount": Decimal("0"),
        "payable": Decimal("0"),
    }

    prepared_rows = []

    def fmt_money(val):
        if isinstance(val, Decimal):
            return f"{val:.2f}"
        return str(val)

    def decimal_to_time(decimal_hours):
        if not decimal_hours:
            return "0:00"
        hours = int(decimal_hours)
        minutes = int((decimal_hours - hours) * 60)
        return f"{hours}:{minutes:02d}"

    for idx, stat in enumerate(stats, start=1):
        emp = stat["employee"]
        
        # Accumulate totals
        totals_acc["basic"] += stat["basic_salary"] or Decimal(0)
        totals_acc["house_rent"] += stat["house_rent"] or Decimal(0)
        totals_acc["medical"] += stat["medical_allowance"] or Decimal(0)
        totals_acc["conv"] += stat["conveyance_allowance"] or Decimal(0)
        totals_acc["food"] += stat["food_allowance"] or Decimal(0)
        totals_acc["other"] += stat["other_allowance"] or Decimal(0)
        totals_acc["gross"] += stat["gross_salary"] or Decimal(0)
        totals_acc["wd"] += stat["working_days"]
        totals_acc["wkn"] += stat["weekends"]
        totals_acc["l"] += stat["leave_days"]
        totals_acc["h"] += stat["holidays"]
        totals_acc["att"] += stat["attended_days"]
        totals_acc["late"] += stat["late_days"] # Added
        totals_acc["ot_hours"] += stat["ot_hours"] or Decimal(0)
        totals_acc["ot_rate"] += stat["ot_rate"] or Decimal(0)
        totals_acc["ot_amt"] += stat["ot_amount"] or Decimal(0)
        totals_acc["hd_allow"] += stat["hd_allowance"] or Decimal(0)
        totals_acc["att_bonus"] += stat["attendance_bonus"] or Decimal(0)
        totals_acc["other_deduct"] += stat["other_deduction"] or Decimal(0)
        totals_acc["late_fine"] += stat["late_fine"] or Decimal(0) # Added
        totals_acc["tds_amount"] += stat["tds_amount"] or Decimal(0)
        totals_acc["payable"] += stat["payable"] or Decimal(0)

        row_data = [
            str(idx),
            f"{emp.name}\n({emp.employee_id})",
            emp.hire_date.isoformat() if emp.hire_date else "-",
            emp.bank_account or "-",
            fmt_money(stat["basic_salary"]),
            fmt_money(stat["house_rent"]),
            fmt_money(stat["medical_allowance"]),
            fmt_money(stat["conveyance_allowance"]),
            fmt_money(stat["food_allowance"]),
            fmt_money(stat["other_allowance"]),
            fmt_money(stat["gross_salary"]),
            str(stat["working_days"]),
            str(stat["weekends"]),
            str(stat["leave_days"]),
            str(stat["holidays"]),
            str(stat["attended_days"]),
            str(stat["late_days"]), # Added
            decimal_to_time(stat["ot_hours"]), # Format as HH:MM
            fmt_money(stat["ot_rate"]),
            fmt_money(stat["ot_amount"]),
            fmt_money(stat["hd_allowance"]),
            fmt_money(stat["attendance_bonus"]),
            fmt_money(stat["other_deduction"]),
            fmt_money(stat["late_fine"]), # Added
            (stat["tds_percent"], stat["tds_amount"]),
            fmt_money(stat["payable"]),
            "", # Signature
        ]
        prepared_rows.append(row_data)

        # Measure row
        for i, val in enumerate(row_data):
            if i == 24: # TDS (index shifted by +1 due to Fine)
                p, a = val
                p_str = f"{p:.2f}%" if isinstance(p, Decimal) else str(p)
                a_str = f"{a:.2f}" if isinstance(a, Decimal) else str(a)
                w = max(pdf.stringWidth(p_str, "Helvetica", 7), pdf.stringWidth(a_str, "Helvetica", 6))
            else:
                w = pdf.stringWidth(val, "Helvetica", 7)
            col_widths[i] = max(col_widths[i], w + padding)

    # Prepare and measure totals row
    totals_row = [
        "", # S/N
        get_moderator_label("salary_totals_label", "TOTALS"), # Name
        "", # Joining
        "", # Bank
        fmt_money(totals_acc["basic"]),
        fmt_money(totals_acc["house_rent"]),
        fmt_money(totals_acc["medical"]),
        fmt_money(totals_acc["conv"]),
        fmt_money(totals_acc["food"]),
        fmt_money(totals_acc["other"]),
        fmt_money(totals_acc["gross"]),
        str(totals_acc["wd"]),
        str(totals_acc["wkn"]),
        str(totals_acc["l"]),
        str(totals_acc["h"]),
        str(totals_acc["att"]),
        str(totals_acc["late"]), # Added
        decimal_to_time(totals_acc["ot_hours"]), # Format as HH:MM
        fmt_money(totals_acc["ot_rate"]),
        fmt_money(totals_acc["ot_amt"]),
        fmt_money(totals_acc["hd_allow"]),
        fmt_money(totals_acc["att_bonus"]),
        fmt_money(totals_acc["other_deduct"]),
        fmt_money(totals_acc["late_fine"]), # Added
        fmt_money(totals_acc["tds_amount"]),
        fmt_money(totals_acc["payable"]),
        "", # Signature
    ]
    
    for i, val in enumerate(totals_row):
        w = pdf.stringWidth(val, "Helvetica-Bold", 7)
        col_widths[i] = max(col_widths[i], w + padding)



    # Calculate positions
    col_positions = []
    x = margin
    for w in col_widths:
        col_positions.append(x)
        x += w
    table_width = x - margin
    available_width = width - 2 * margin
    if table_width < available_width:
        scale = available_width / table_width
        col_widths = [w * scale for w in col_widths]
        col_positions = []
        x = margin
        for w in col_widths:
            col_positions.append(x)
            x += w
    table_right = x
    row_height = 20

    def draw_salary_headers():
        nonlocal y
        top_y = y
        bottom_y = y - row_height
        pdf.setFillColorRGB(*subheader_fill)
        pdf.rect(margin, bottom_y, table_right - margin, row_height, stroke=0, fill=1)
        pdf.setFillColorRGB(1, 1, 1)
        pdf.setFont("Helvetica-Bold", 8)
        
        for (label, align), xpos, width in zip(headers, col_positions, col_widths):
            lines = label.split('\n')
            if len(lines) == 1:
                line_y_offsets = [7]
            else:
                line_y_offsets = [11, 3]
            
            for line, y_off in zip(lines, line_y_offsets):
                draw_y = bottom_y + y_off
                if align == "right":
                    pdf.drawRightString(xpos + width - 2, draw_y, line)
                elif align == "center":
                    pdf.drawCentredString(xpos + width / 2, draw_y, line)
                else:
                    pdf.drawString(xpos + 2, draw_y, line)

        pdf.setStrokeColorRGB(*grid_color)
        pdf.setLineWidth(0.6)
        pdf.line(margin, bottom_y, table_right, bottom_y)
        for xpos in col_positions:
            pdf.line(xpos, top_y, xpos, bottom_y)
        pdf.line(table_right, top_y, table_right, bottom_y)
        y = bottom_y

    def ensure_space():
        nonlocal y
        if y <= margin + row_height * 2:
            pdf.showPage()
            y = height - margin
            draw_salary_headers()

    draw_salary_headers()
    pdf.setFont("Helvetica", 7)

    for idx, row_data in enumerate(prepared_rows, start=1):
        ensure_space()
        top_y = y
        bottom_y = y - row_height
        fill = row_fill_primary if idx % 2 else row_fill_secondary
        pdf.setFillColorRGB(*fill)
        pdf.rect(margin, bottom_y, table_right - margin, row_height, stroke=0, fill=1)
        pdf.setFillColorRGB(0, 0, 0)
        
        for i, ((label, align), xpos, width, value) in enumerate(zip(headers, col_positions, col_widths, row_data)):
            if i == 24: # TDS (index shifted by +1 due to Fine)
                percent, amount = value
                perc_display = f"{percent:.2f}%" if isinstance(percent, Decimal) else str(percent)
                amt_display = f"{amount:.2f}" if isinstance(amount, Decimal) else str(amount)
                pdf.drawCentredString(xpos + width / 2, bottom_y + 11, perc_display)
                pdf.setFont("Helvetica", 6)
                pdf.drawCentredString(xpos + width / 2, bottom_y + 4, amt_display)
                pdf.setFont("Helvetica", 7)
                continue
            
            if align == "right":
                pdf.drawRightString(xpos + width - 2, bottom_y + 8, value)
            elif align == "center":
                pdf.drawCentredString(xpos + width / 2, bottom_y + 8, value)
            else:
                pdf.drawString(xpos + 2, bottom_y + 8, value)
                
        pdf.setStrokeColorRGB(*grid_color)
        pdf.setLineWidth(0.6)
        # Vertical lines
        for xpos in col_positions:
            pdf.line(xpos, top_y, xpos, bottom_y)
        pdf.line(table_right, top_y, table_right, bottom_y)
        # Horizontal line
        pdf.line(margin, bottom_y, table_right, bottom_y)
        y = bottom_y

    # Draw Totals
    ensure_space()
    top_y = y
    bottom_y = y - row_height
    pdf.setFillColorRGB(*totals_fill)
    pdf.rect(margin, bottom_y, table_right - margin, row_height, stroke=0, fill=1)
    pdf.setFillColorRGB(1, 1, 1)
    pdf.setFont("Helvetica-Bold", 7)
    
    for i, ((label, align), xpos, width, value) in enumerate(zip(headers, col_positions, col_widths, totals_row)):
        if i == 0: continue # Skip S/N
        if i == 1:  # Name column
            merged_width = col_widths[0] + col_widths[1]
            center_x = col_positions[0] + merged_width / 2
            pdf.drawCentredString(center_x, bottom_y + 8, get_moderator_label("salary_totals_label", "TOTALS"))
            continue
        
        if not value: continue

        if align == "right":
            pdf.drawRightString(xpos + width - 2, bottom_y + 8, value)
        elif align == "center":
            pdf.drawCentredString(xpos + width / 2, bottom_y + 8, value)
        else:
            pdf.drawString(xpos + 2, bottom_y + 8, value)
            
    pdf.setStrokeColorRGB(*grid_color)
    pdf.setLineWidth(0.6)
    for i, xpos in enumerate(col_positions):
        if i == 1: continue # Skip line between S/N and Name
        pdf.line(xpos, top_y, xpos, bottom_y)
    pdf.line(table_right, top_y, table_right, bottom_y)
    pdf.line(margin, bottom_y, table_right, bottom_y)

    pdf.save()
    return response


def _ensure_salary_statistics(selected_year, selected_month, employees_qs, days_in_month):
    from datetime import datetime
    from .models import SalaryStatisticDefault
    merged_stats = []
    default_template = SalaryStatisticDefault.objects.first()
    for emp in employees_qs:
        stat, _ = SalaryStatistic.objects.get_or_create(
            employee=emp,
            month=selected_month,
            year=selected_year,
            defaults={
                "basic_salary": emp.monthly_salary,
                "gross_salary": emp.monthly_salary,
                "payable": emp.monthly_salary,
            },
        )
        changed = False
        if default_template and stat.use_default:
            for field in [
                "house_rent",
                "medical_allowance",
                "conveyance_allowance",
                "food_allowance",
                "other_allowance",
                "ot_rate",
                "hd_allowance",
                "attendance_bonus",
                "late_fine",
                "tds_percent",
                "stamp",
            ]:
                current = getattr(stat, field)
                default_val = getattr(default_template, field)
                is_zero = False
                if isinstance(current, Decimal):
                    is_zero = current == 0
                elif isinstance(current, (int, float)):
                    is_zero = current == 0
                elif isinstance(current, bool):
                    # For booleans, if use_default is True, we enforce the default value.
                    # This means if default is True, and current is False, it will be set to True.
                    # If default is False, and current is True, it will be set to False.
                    if getattr(stat, field) != getattr(default_template, field):
                        setattr(stat, field, getattr(default_template, field))
                        changed = True
                    continue # Skip the is_zero check for booleans
                else:
                    is_zero = current in (None, "", 0)
                
                if is_zero:
                    setattr(stat, field, default_val)
                    changed = True
            
            # Removed auto_calculate_bonus and auto_calculate_fine logic


        # Always recompute derived fields to keep admin/PDF in sync
        # Pull attendance-derived counts (real time)
        emp_records = AttendanceRecord.objects.filter(
            employee=emp, date__year=selected_year, date__month=selected_month
        )
        # Calculate Weekends (Fridays) automatically from calendar
        import calendar
        weekends = 0
        for day in range(1, days_in_month + 1):
            # weekday() returns 0=Monday, ..., 4=Friday, ...
            if calendar.weekday(selected_year, selected_month, day) == 4:
                weekends += 1

        leave_days = emp_records.filter(status="On Leave").count()
        holidays = emp_records.filter(status="Holiday").count()
        # Broaden Attended Days to include Late, Early Leave, Half Day
        attended_days = emp_records.filter(status__in=["Present", "Late", "Early Leave", "Half Day"]).count()
        
        # User requested WD = days in a month
        stat.working_days = days_in_month
        stat.weekends = weekends
        stat.leave_days = leave_days
        stat.holidays = holidays
        stat.attended_days = attended_days

        # Calculate Late Days, Fines, and Overtime
        late_days = 0
        total_ot_seconds = 0
        ot_threshold_time = datetime.strptime("18:10", "%H:%M").time()
        
        for record in emp_records:
            if record.status in ['Holiday', 'Off Day']:
                continue
            
            # Late Calculation
            if record.is_late_indicator():
                late_days += 1
                
            # Overtime Calculation (After 6:10 PM)
            if record.checkout_time:
                # Convert to local time (Dhaka)
                local_checkout = record.checkout_time.astimezone(dhaka)
                # Create threshold datetime for the same day
                threshold_dt = local_checkout.replace(
                    hour=ot_threshold_time.hour, 
                    minute=ot_threshold_time.minute, 
                    second=0, 
                    microsecond=0
                )
                
                if local_checkout > threshold_dt:
                    ot_duration = local_checkout - threshold_dt
                    total_ot_seconds += ot_duration.total_seconds()
        
        # Update the statistic with the calculated late days
        stat.late_days = late_days
        
        # Convert OT seconds to hours
        ot_hours = Decimal(total_ot_seconds) / Decimal(3600)
        stat.ot_hours = ot_hours

        # Fine Calculation (Configurable)
        if default_template:
            fine_amount = Decimal("0.00")
            threshold = stat.late_needed
            unit_fine = default_template.late_fine
            
            if threshold > 0 and late_days >= threshold:
                fine_groups = late_days // threshold
                fine_amount = unit_fine * fine_groups
            
            stat.late_fine = fine_amount

        # Bonus Calculation (Configurable)
        if default_template:
            bonus_amt = Decimal("0.00")
            threshold_percent = stat.required_attendance_percent
            base_bonus = default_template.attendance_bonus
            
            if threshold_percent > 0:
                # Percentage based calculation
                # Calculate actual working days (excluding weekends and holidays)
                actual_working_days = days_in_month - weekends - holidays
                
                if actual_working_days > 0:
                    # attended_days includes Present, Late, Early Leave, Half Day
                    # We assume all these count towards "Attendance" for the purpose of the bonus
                    current_percent = (Decimal(attended_days) / Decimal(actual_working_days)) * 100
                    
                    if current_percent >= threshold_percent:
                        bonus_amt = base_bonus
            else:
                # Fallback to "Perfect Attendance" rule if threshold is 0
                # Rule: 100% Present (no late, no leave, no absent, no half day)
                is_perfect = True
                if late_days > 0:
                    is_perfect = False
                else:
                    for r in emp_records:
                        if r.status in ['Holiday', 'Off Day']:
                            continue
                        if r.status != 'Present':
                            is_perfect = False
                            break
                
                if is_perfect:
                    bonus_amt = base_bonus
            
            stat.attendance_bonus = bonus_amt


        stat.ot_amount = stat.ot_hours * stat.ot_rate
        stat.gross_salary = (
            stat.basic_salary
            + stat.house_rent
            + stat.medical_allowance
            + stat.conveyance_allowance
            + stat.food_allowance
            + stat.other_allowance
        )
        
        # New Tax Logic: 
        # Taxable = (100% Basic + 100% OT) + 66.66% (Allowances) - Other Deduct
        # Allowances = Rent + Med + Conv + Food + Other + HD + Bonus
        tds_amount = Decimal("0.00")
        if stat.tds_percent:
            total_allowances = (
                stat.house_rent
                + stat.medical_allowance
                + stat.conveyance_allowance
                + stat.food_allowance
                + stat.other_allowance
                + stat.hd_allowance
                + stat.attendance_bonus
            )
            
            # Deduct fines and other deductions from allowances before applying tax factor
            net_allowances = total_allowances - stat.late_fine - stat.other_deduction
            if net_allowances < 0:
                net_allowances = Decimal("0.00")
                
            taxable_others = net_allowances * Decimal("0.6666")
            
            taxable_income = stat.basic_salary + stat.ot_amount + taxable_others
            
            # Ensure taxable income isn't negative
            if taxable_income < 0:
                taxable_income = Decimal("0.00")
                
            tds_amount = (taxable_income * stat.tds_percent) / Decimal("100")
            
        # Update payable to include fine deduction and other deduction
        stat.payable = (
            stat.gross_salary 
            + stat.ot_amount 
            + stat.hd_allowance 
            + stat.attendance_bonus 
            - stat.late_fine # Deduct late fine
            - stat.other_deduction
            - tds_amount 
            - stat.stamp 
        )
        
        # Always save to persist the dynamic updates
        stat.save()

        merged_stats.append(
            {
                "employee": emp,
                "basic_salary": stat.basic_salary,
                "house_rent": stat.house_rent,
                "medical_allowance": stat.medical_allowance,
                "conveyance_allowance": stat.conveyance_allowance,
                "food_allowance": stat.food_allowance,
                "other_allowance": stat.other_allowance,
                "gross_salary": stat.gross_salary,
                "working_days": stat.working_days,
                "weekends": stat.weekends,
                "leave_days": stat.leave_days,
                "holidays": stat.holidays,
                "attended_days": stat.attended_days,
                "ot_hours": stat.ot_hours,
                "ot_rate": stat.ot_rate,
                "ot_amount": stat.ot_amount,
                "hd_allowance": stat.hd_allowance,
                "attendance_bonus": stat.attendance_bonus,
                "other_deduction": stat.other_deduction,
                "late_fine": stat.late_fine, # Added to merged_stats
                "tds_percent": stat.tds_percent,
                "tds_amount": tds_amount,
                "stamp": stat.stamp,
                "payable": stat.payable,
                
                # Aliases for HTML Report (salary-report-new.html)
                "base_salary": stat.basic_salary,
                "total_bonus": stat.attendance_bonus,
                "total_fine": stat.late_fine, # Use stat.late_fine here
                "final_salary": stat.payable,
                "late_days": late_days,
            }
        )
    return merged_stats


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


def _render_attendance_pdf(
    selected_year,
    selected_month,
    selected_department,
    selected_designation,
    today,
    days_in_month,
    employees_qs,
    single_employee_id=None,
    record_map=None,
    active_shift=None,
    theme="classic",
    detailed_report=False,
):
    from datetime import datetime

    days = build_days(selected_year, selected_month, days_in_month)
    record_map = record_map or build_record_map(selected_year, selected_month)
    active_shift = active_shift or get_active_shift()
    is_single_employee = single_employee_id is not None and employees_qs.count() == 1
    show_details = is_single_employee or detailed_report

    dashboard_rows = []
    for emp in employees_qs:
        statuses, totals, _ = build_employee_row(
            emp,
            days,
            today,
            record_map,
            active_shift,
        )
        dashboard_rows.append(
            {
                "employee": emp,
                "statuses": statuses,
                "totals": totals,
            }
        )

    month_label = datetime(selected_year, selected_month, 1).strftime("%B %Y")
    filename = f"attendance-dashboard-{selected_year}-{selected_month}.pdf"
    if is_single_employee and dashboard_rows:
        emp_for_name = dashboard_rows[0]["employee"]
        safe_emp_id = emp_for_name.employee_id or emp_for_name.id
        filename = f"attendance-{safe_emp_id}-{selected_year}-{selected_month}.pdf"

    buffer = BytesIO()
    from reportlab.lib.pagesizes import legal
    page_size = landscape(legal)
    pdf = canvas.Canvas(buffer, pagesize=page_size)
    width, height = page_size
    margin = 20
    y = height - margin

    # Apply palettes: lighter base for colorburst, deep accents for customdark
    theme = (theme or "light").lower()
    if theme == "customdark":
        # For visibility, map customdark to the bright salary palette
        page_bg = (1, 1, 1)
        header_fill = (0.12, 0.55, 0.32)   # green
        subheader_fill = (0.72, 0.16, 0.28) # red
        row_fill_primary = (0.98, 0.99, 0.97)
        row_fill_secondary = (0.94, 0.97, 0.92)
        totals_fill = (0.16, 0.36, 0.60)    # deep blue
        grid_color = (0.70, 0.78, 0.74)
        title_color = (1, 1, 1)
        text_color = (0.12, 0.20, 0.24)
    elif theme == "colorburst":
        page_bg = (1, 1, 1)
        header_fill = (0.12, 0.55, 0.32)   # green
        subheader_fill = (0.72, 0.16, 0.28) # red
        row_fill_primary = (0.98, 0.99, 0.97)
        row_fill_secondary = (0.94, 0.97, 0.92)
        totals_fill = (0.16, 0.36, 0.60)    # deep blue
        grid_color = (0.70, 0.78, 0.74)
        title_color = (1, 1, 1)
        text_color = (0.12, 0.20, 0.24)
    elif theme == "dark":
        page_bg = (0.06, 0.08, 0.10)
        header_fill = (0.50, 0.06, 0.12)
        subheader_fill = (0.16, 0.40, 0.26)
        row_fill_primary = (0.14, 0.16, 0.18)
        row_fill_secondary = (0.16, 0.19, 0.21)
        totals_fill = (0.10, 0.28, 0.44)
        grid_color = (0.55, 0.62, 0.60)
        title_color = (1, 1, 1)
        text_color = (0.94, 0.96, 0.98)
    else:
        page_bg = (1, 1, 1)
        header_fill = (0.14, 0.48, 0.30)  # green
        subheader_fill = (0.16, 0.36, 0.58)  # blue-green
        row_fill_primary = (0.99, 0.99, 0.99)
        row_fill_secondary = (0.96, 0.98, 0.95)
        totals_fill = (0.16, 0.36, 0.58)
        grid_color = (0.70, 0.78, 0.76)
        title_color = (1, 1, 1)
        text_color = (0.12, 0.20, 0.24)

    title_bar_height = 32

    # Draw Page Background
    header_height = 110
    pdf.setFillColorRGB(*page_bg)
    pdf.rect(0, 0, width, height, stroke=0, fill=1)

    pdf.setFillColorRGB(*header_fill)
    pdf.rect(0, height - header_height, width, header_height, stroke=0, fill=1)
    
    # Draw Company Info
    company = CompanyInfo.get_solo()
    pdf.setFillColorRGB(1, 1, 1)

    # Logo (left), text centered
    if company.logo:
        try:
            pdf.drawImage(company.logo.path, margin, height - 70, width=60, height=60, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

    center_x = width / 2
    pdf.setFont("Helvetica-Bold", 18)
    name_y = height - header_height + 70
    pdf.drawCentredString(center_x, name_y, company.name)

    pdf.setFont("Helvetica", 10)
    y_offset = name_y - 18
    if company.address:
        pdf.drawCentredString(center_x, y_offset, company.address)
        y_offset -= 12
    if company.email:
        pdf.drawCentredString(center_x, y_offset, f"Email: {company.email}")
        y_offset -= 12
    if company.phone:
        pdf.drawCentredString(center_x, y_offset, f"Phone: {company.phone}")
        y_offset -= 12
    if getattr(company, "tin", None):
        pdf.drawCentredString(center_x, y_offset, f"TIN: {company.tin}")
        y_offset -= 12
    if getattr(company, "bin", None):
        pdf.drawCentredString(center_x, y_offset, f"BIN/BFN: {company.bin}")
        y_offset -= 12
    if getattr(company, "founder", None):
        pdf.drawCentredString(center_x, y_offset, f"Founder: {company.founder}")

    # Drop the table start below the header block
    y = height - margin - header_height + 20

    dashboard_title = f"{get_moderator_label('attendance_dashboard_title', 'Attendance Dashboard')} - {month_label}"
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(margin, height - header_height + 15, dashboard_title)
    y -= 20

    pdf.setFillColorRGB(*text_color)
    pdf.setFont("Helvetica", 10)
    if selected_department:
        pdf.drawString(margin, y, f"Department: {selected_department}")
        y -= 12
    if selected_designation:
        pdf.drawString(margin, y, f"Designation: {selected_designation}")
        y -= 12
    y -= 4

    # Legend will be placed at the bottom

    # Layout dimensions: expand table for detailed (combined), keep readable for others (legal landscape)
    name_col = margin + 4
    if detailed_report:
        name_col_width = 240
        day_start = margin + name_col_width
        available_width = (width - margin) - day_start
        day_width = min(22, max(14, available_width / len(days)))
        table_right = width - margin
    else:
        name_col_width = 240
        day_start = margin + name_col_width
        available_width = (width - margin) - day_start
        day_width = max(14, available_width / len(days))
        table_right = width - margin
    row_height = 16
    small_row_height = 14

    # Scale table typography ~30% larger without changing cell geometry
    font_scale = 1.3
    header_employee_font = max(10, int(round(10 * font_scale)))
    header_day_font = max(9, int(round(9 * font_scale)))
    body_font = max(8, int(round(8 * font_scale)))
    status_font = max(6, int(round(6 * font_scale)))
    detail_label_font = max(10, int(round(10 * font_scale)))
    detail_label_baseline_font = max(7, int(round(7 * font_scale)))
    # Time text slightly smaller (40% reduction) to keep within cells
    detail_time_font = max(6, int(round(9 * font_scale * 0.6)))
    ampm_font = max(5, int(round(6 * font_scale * 0.6)))
    header_top_padding = 4
    cell_top_padding = 2
    time_bottom_padding = 2

    def format_time(dt):
        if not dt:
            return ("-", "")
        try:
            parts = dt.astimezone(dhaka).strftime("%I:%M %p").lstrip("0").split()
            if len(parts) == 2:
                return parts[0], parts[1]
            return (parts[0], "") if parts else ("-", "")
        except Exception:
            return ("-", "")

    def center_text(x_start, col_width, text, y_pos):
        center_x = x_start + col_width / 2
        pdf.drawCentredString(center_x, y_pos, text)

    def baseline_for_row(row_bottom, height, font_size):
        return row_bottom + (height * 0.45) + (font_size * 0.05)

    def padded_baseline(row_bottom, height, font_size, factor=1.0):
        """
        Push text further down inside the cell by a multiplier factor (>1 adds padding from top).
        """
        base = baseline_for_row(row_bottom, height, font_size)
        return base + (factor - 1.0) * (height * 0.2)

    column_lines = [margin, day_start]
    for idx in range(len(days) + 1):
        column_lines.append(day_start + idx * day_width)
    column_lines.append(table_right)
    column_lines = sorted(set(column_lines))

    def draw_row_grid(top_y, bottom_y, draw_top=True, draw_bottom=True):
        pdf.setStrokeColorRGB(*grid_color)
        pdf.setLineWidth(0.6)
        if draw_top:
            pdf.line(margin, top_y, table_right, top_y)
        if draw_bottom:
            pdf.line(margin, bottom_y, table_right, bottom_y)
        for x in column_lines:
            pdf.line(x, top_y, x, bottom_y)

    def draw_headers():
        nonlocal y
        top_y = y
        bottom_y = y - row_height
        pdf.setLineWidth(0.8)
        pdf.setFillColorRGB(*subheader_fill)
        pdf.rect(margin - 1, bottom_y, table_right - margin + 2, row_height, stroke=0, fill=1)
        pdf.setFillColorRGB(*title_color)
        pdf.setFont("Helvetica-Bold", header_employee_font)
        header_text_y = baseline_for_row(bottom_y, row_height, header_employee_font) - header_top_padding
        pdf.drawString(name_col, header_text_y, get_moderator_label("attendance_employee_header", "Employee"))
        pdf.setFont("Helvetica-Bold", header_day_font)
        for idx, day in enumerate(days):
            center_text(
                day_start + idx * day_width,
                day_width,
                str(day["num"]),
                baseline_for_row(bottom_y, row_height, header_day_font) - header_top_padding,
            )
        draw_row_grid(top_y, bottom_y)
        y = bottom_y  # next row starts exactly at current bottom to keep lines connected

    def ensure_space():
        nonlocal y
        needed_height = 3 * row_height if show_details else 2 * row_height
        if y <= margin + needed_height:
            pdf.showPage()
            y = height - margin
            draw_headers()

    pdf.setStrokeColorRGB(0.4, 0.4, 0.45)
    draw_headers()
    pdf.setFont("Helvetica", body_font)
    for row_index, row in enumerate(dashboard_rows):
        ensure_space()
        row_top = y
        row_bottom = y - row_height
        text_y_main = baseline_for_row(row_bottom, row_height, body_font) - cell_top_padding
        pdf.setLineWidth(0.6)
        if row_index % 2 == 0:
            pdf.setFillColorRGB(*row_fill_primary)
        else:
            pdf.setFillColorRGB(*row_fill_secondary)
        pdf.rect(margin - 1, row_bottom, table_right - margin + 2, row_height, stroke=0, fill=1)
        pdf.setFillColorRGB(*text_color)
        employee_label = f"{row['employee'].name}"
        pdf.drawString(name_col, text_y_main, employee_label[:40])
        pdf.setFont("Helvetica", status_font)
        for idx, status_entry in enumerate(row["statuses"]):
            label = _status_to_label(status_entry)
            xpos = day_start + idx * day_width
            is_late = status_entry.get("is_late")
            if is_late:
                pdf.setFillColorRGB(0.8, 0.0, 0.0)
            if label.endswith("!"):
                pdf.setFillColorRGB(*text_color)
                center_text(xpos, day_width, label[:-1], text_y_main)
                pdf.setFillColorRGB(0.8, 0.0, 0.0)
                center_text(xpos + (day_width * 0.35), day_width, "!", text_y_main + 4)
                pdf.setFillColorRGB(*text_color)
            else:
                center_text(xpos, day_width, label, text_y_main)
            if is_late:
                pdf.setFillColorRGB(*text_color)
        pdf.setFont("Helvetica", body_font)
        if show_details:
            y = row_bottom  # start subrows immediately below main row
            pdf.setFont("Helvetica-Bold", detail_label_font)
            checkin_top = y
            checkin_bottom = y - row_height  # match main row height and padding
            checkin_text_y = baseline_for_row(checkin_bottom, row_height, detail_label_baseline_font) - cell_top_padding
            pdf.drawString(name_col, checkin_text_y, "Check-in")
            pdf.setFont("Helvetica", detail_time_font)
            for idx, day in enumerate(days):
                record = record_map.get((row["employee"].id, day["num"]))
                late_flag = record.is_late_indicator() if record else False
                time_parts = format_time(record.checkin_time) if record else ("-", "")
                if late_flag:
                    pdf.setFillColorRGB(0.8, 0.0, 0.0)
                if record and record.status == "Pending":
                    # Pending normally green, but late overrides to red
                    pdf.setFillColorRGB(0.1, 0.5, 0.1)
                    if late_flag:
                        pdf.setFillColorRGB(0.8, 0.0, 0.0)
                center_text(
                    day_start + idx * day_width,
                    day_width,
                    time_parts[0],
                    checkin_text_y + time_bottom_padding,
                )
                if time_parts[1]:
                    pdf.setFont("Helvetica", ampm_font)
                    center_text(
                        day_start + idx * day_width,
                        day_width,
                        time_parts[1],
                        checkin_text_y - ampm_font + time_bottom_padding,
                    )
                    pdf.setFont("Helvetica", detail_time_font)
                if late_flag or (record and record.status == "Pending"):
                    pdf.setFillColorRGB(0, 0, 0)
            draw_row_grid(checkin_top, checkin_bottom)

            checkout_top = checkin_bottom
            checkout_bottom = checkout_top - row_height
            checkout_text_y = baseline_for_row(checkout_bottom, row_height, detail_label_baseline_font) - cell_top_padding
            pdf.setFont("Helvetica-Bold", detail_label_font)
            pdf.drawString(name_col, checkout_text_y, "Check-out")
            pdf.setFont("Helvetica", detail_time_font)
            for idx, day in enumerate(days):
                record = record_map.get((row["employee"].id, day["num"]))
                late_flag = record.is_late_indicator() if record else False
                time_parts = format_time(record.checkout_time) if record else ("-", "")
                if late_flag:
                    pdf.setFillColorRGB(0.8, 0.0, 0.0)
                center_text(
                    day_start + idx * day_width,
                    day_width,
                    time_parts[0],
                    checkout_text_y + time_bottom_padding,
                )
                if time_parts[1]:
                    pdf.setFont("Helvetica", ampm_font)
                    center_text(
                        day_start + idx * day_width,
                        day_width,
                        time_parts[1],
                        checkout_text_y - ampm_font + time_bottom_padding,
                    )
                    pdf.setFont("Helvetica", detail_time_font)
                if late_flag:
                    pdf.setFillColorRGB(0, 0, 0)
            draw_row_grid(checkout_top, checkout_bottom)
            pdf.setFont("Helvetica", body_font)
            y = checkout_bottom
        else:
            y = row_bottom
        draw_row_grid(row_top, row_bottom)

    # Bottom legend (moved from top)
    pdf.setFont("Helvetica", 8)
    pdf.setFillColorRGB(*text_color)
    legend_entries = [f"{abbr} = {name}" for name, abbr in STATUS_LABEL_MAP.items()]
    legend_y = margin + 20
    pdf.drawString(margin, legend_y, "Legend: " + " | ".join(legend_entries))
    pdf.setFillColorRGB(0.5, 0.5, 0.5)
    pdf.drawString(margin, legend_y - 12, "(! indicates the employee arrived late on that day)")
    pdf.setFillColorRGB(*text_color)

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer.getvalue(), filename


@staff_member_required
def moderator_edit_view(request):
    from django.contrib import messages
    from django.shortcuts import redirect
    from .utils.moderator_labels import DEFAULT_LABELS, get_label, clear_label_cache

    query = (request.GET.get("q") or "").strip().lower()
    labels = []
    for key, default in DEFAULT_LABELS.items():
        if query and query not in key.lower() and query not in default.lower():
            continue
        labels.append(
            {
                "key": key,
                "default": default,
                "value": get_label(key, default),
            }
        )

    if request.method == "POST":
        key = request.POST.get("key")
        if key and key in DEFAULT_LABELS:
            value = (request.POST.get("value") or "").strip()
            if request.POST.get("reset"):
                ModeratorLabel.objects.filter(key=key).delete()
                clear_label_cache()
                messages.success(request, f"Reset label '{key}'.")
            else:
                ModeratorLabel.objects.update_or_create(
                    key=key,
                    defaults={"label": value},
                )
                clear_label_cache()
                messages.success(request, f"Saved label '{key}'.")
        else:
            messages.error(request, "Unknown label key.")
        redirect_url = request.path
        if query:
            redirect_url += f"?q={query}"
        return redirect(redirect_url)

    context = {
        "query": query,
        "labels": labels,
    }
    return TemplateResponse(request, "admin/moderator_edit.html", context)


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


@staff_member_required
def attendance_dashboard_pdf_combined(request):
    """
    Generate a single PDF containing detailed attendance (check-in/out) for ALL filtered employees.
    """
    from datetime import datetime
    import calendar
    
    try:
        month = int(request.GET.get("month", datetime.now().month))
        year = int(request.GET.get("year", datetime.now().year))
    except ValueError:
        month = datetime.now().month
        year = datetime.now().year

    department = request.GET.get("department")
    designation = request.GET.get("designation")
    search_query = request.GET.get("search")

    employees = Employee.objects.filter(is_active=True)
    if department:
        employees = employees.filter(department=department)
    if designation:
        employees = employees.filter(designation=designation)
    if search_query:
        employees = employees.filter(
            Q(name__icontains=search_query)
            | Q(employee_id__icontains=search_query)
            | Q(designation__icontains=search_query)
        )

    # Sort by ID
    employees = employees.order_by("employee_id")

    today = datetime.now().date()
    _, days_in_month = calendar.monthrange(year, month)

    pdf_content, filename = _render_attendance_pdf(
        year,
        month,
        department,
        designation,
        today,
        days_in_month,
        employees,
        employees,
        detailed_report=True,
        theme=request.GET.get("theme", "light"),
    )

    response = HttpResponse(pdf_content, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="combined-{filename}"'
    return response
