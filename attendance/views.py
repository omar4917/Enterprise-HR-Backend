from django.views.decorators.csrf import csrf_exempt
import calendar
import csv
import io
from datetime import datetime, date, timedelta
from urllib.parse import urlencode

from django.contrib.admin.views.decorators import staff_member_required
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseRedirect,
    JsonResponse,
)
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.encoding import smart_str

from .models import AttendanceRecord, Employee, get_active_shift, dhaka_now

# ---------------------------------------------------------------------
# OPTIONAL XLSX SUPPORT
# ---------------------------------------------------------------------
try:
    import openpyxl
    from openpyxl import Workbook

    HAS_OPENPYXL = True
except Exception:
    HAS_OPENPYXL = False


# =====================================================================
# HELPER BLOCK 1: DASHBOARD PARAMS & NAVIGATION
# =====================================================================
def get_dashboard_params(request):
    """Read selected month/year & filters from request."""
    selected_month = int(request.GET.get("month", datetime.now().month))
    selected_year = int(request.GET.get("year", datetime.now().year))
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


# =====================================================================
# HELPER BLOCK 2: IMPORT (CSV / XLSX)
# =====================================================================
def read_import_file(upload_file):
    """
    Return (headers, rows_iter) for CSV or XLSX.
    headers: list[str]
    rows_iter: list[list[Any]]
    """
    headers = []
    rows_iter = []
    filename = getattr(upload_file, "name", "upload")
    content_type = upload_file.content_type

    # Try Excel first (if openpyxl available and looks like spreadsheet)
    if HAS_OPENPYXL and (
        filename.lower().endswith((".xlsx", ".xlsm")) or "spreadsheet" in content_type
    ):
        wb = openpyxl.load_workbook(
            filename=io.BytesIO(upload_file.read()), data_only=True
        )
        ws = wb.active
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i == 0:
                headers = [str(c).strip() if c is not None else "" for c in row]
                continue
            rows_iter.append(list(row))
    else:
        text = upload_file.read().decode("utf-8-sig")
        reader = csv.reader(io.StringIO(text))
        for i, row in enumerate(reader):
            if i == 0:
                headers = [c.strip() for c in row]
                continue
            rows_iter.append(row)

    return headers, rows_iter


def build_header_mapping(headers):
    """
    Map normalized headers to logical fields.
    Returns dict like {'employee_id': idx, 'date': idx, ...}
    """
    headers_norm = [h.lower() for h in headers]
    mapping = {}

    for idx, h in enumerate(headers_norm):
        if "employee" in h and "id" in h:
            mapping["employee_id"] = idx
        elif h == "employee_id":
            mapping["employee_id"] = idx
        elif h == "date":
            mapping["date"] = idx
        elif "checkin" in h:
            mapping["checkin_time"] = idx
        elif "checkout" in h:
            mapping["checkout_time"] = idx
        elif "status" in h:
            mapping["status"] = idx
        elif "late" in h and "second" in h:
            mapping["late_seconds"] = idx

    return mapping


def parse_any_date(raw_date_str, raw_cell):
    """
    Try multiple date formats:
    - ISO (YYYY-MM-DD)
    - DD/MM/YYYY
    - MM/DD/YYYY
    - Excel numeric (if raw_cell is int/float)
    Return date or None.
    """
    if not raw_date_str:
        return None

    # Try ISO
    try:
        return date.fromisoformat(raw_date_str)
    except Exception:
        pass

    # dd/mm/yyyy
    for fmt in ("%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(raw_date_str, fmt).date()
        except Exception:
            continue

    # Excel numeric date as fallback
    if isinstance(raw_cell, (int, float)):
        try:
            return date(1899, 12, 30) + timedelta(days=float(raw_cell))
        except Exception:
            pass

    return None


def parse_any_time(raw_value, parsed_date):
    """
    Parse string time formats:
    - HH:MM:SS
    - HH:MM
    - full ISO datetime
    Return datetime or None.
    """
    if raw_value in (None, ""):
        return None

    raw_str = str(raw_value).strip()

    # Full ISO datetime
    try:
        dt = datetime.fromisoformat(raw_str)
        return dt if dt.tzinfo else dt.replace(tzinfo=None)
    except Exception:
        pass

    # Time-only formats
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            t = datetime.strptime(raw_str, fmt).time()
            dt = datetime.combine(parsed_date, t)
            return dt if dt.tzinfo else dt.replace(tzinfo=None)
        except Exception:
            continue

    return None


def handle_import(request, selected_year, selected_month):
    """
    Handle import logic.
    Returns (import_errors, import_success)
    """
    import_errors = []
    import_success = None

    if request.method != "POST" or not request.FILES.get("import_file"):
        return import_errors, import_success

    f = request.FILES["import_file"]

    try:
        headers, rows_iter = read_import_file(f)
    except Exception as e:
        import_errors.append(f"Failed to read file: {e}")
        return import_errors, import_success

    mapping = build_header_mapping(headers)

    # require employee_id and date
    if "employee_id" not in mapping or "date" not in mapping:
        import_errors.append("File must include at least columns: employee_id, date")
        return import_errors, import_success

    created = 0
    updated = 0

    for ridx, row in enumerate(rows_iter, start=2):
        try:
            emp_id = (
                str(row[mapping["employee_id"]]).strip()
                if mapping.get("employee_id") is not None
                else ""
            )
            raw_date = (
                str(row[mapping["date"]]).strip()
                if mapping.get("date") is not None
                else ""
            )

            if not emp_id or not raw_date:
                import_errors.append(
                    f"Row {ridx}: missing employee_id or date; skipping"
                )
                continue

            parsed_date = parse_any_date(raw_date, row[mapping["date"]])
            if not parsed_date:
                import_errors.append(f"Row {ridx}: unrecognized date '{raw_date}'")
                continue

            # Only import selected month/year
            if parsed_date.year != selected_year or parsed_date.month != selected_month:
                continue

            # Employee lookup
            try:
                emp = Employee.objects.get(employee_id=emp_id)
            except Employee.DoesNotExist:
                import_errors.append(
                    f"Row {ridx}: employee_id '{emp_id}' not found; skipping"
                )
                continue

            # parse times
            ci = (
                parse_any_time(row[mapping.get("checkin_time")], parsed_date)
                if mapping.get("checkin_time")
                else None
            )
            co = (
                parse_any_time(row[mapping.get("checkout_time")], parsed_date)
                if mapping.get("checkout_time")
                else None
            )

            obj, created_flag = AttendanceRecord.objects.get_or_create(
                employee=emp, date=parsed_date
            )
            changed = False

            if ci is not None and obj.checkin_time != ci:
                obj.checkin_time = ci
                changed = True
            if co is not None and obj.checkout_time != co:
                obj.checkout_time = co
                changed = True

            if mapping.get("status") is not None:
                val = row[mapping["status"]]
                if val not in (None, ""):
                    s = str(val).strip()
                    if obj.status != s:
                        obj.status = s
                        changed = True

            if created_flag:
                obj.save()
                created += 1
            elif changed:
                obj.save()
                updated += 1

        except Exception as e:
            import_errors.append(f"Row {ridx}: unexpected error: {e}")

    import_success = {"created": created, "updated": updated}
    return import_errors, import_success


# =====================================================================
# HELPER BLOCK 3: DASHBOARD DATA BUILD
# =====================================================================
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
            current_date.year if False else day_info["num"], 1, 1
        )  # placeholder to keep lints quiet

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
                    is_late = bool(computed_late and computed_late.total_seconds() > 0)
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

            # update totals
            if display_status == "Present":
                totals["Present"] += 1
            elif display_status == "Late":
                totals["Late"] += 1
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

        statuses.append(
            {
                "day": day_num,
                "status": display_status,
                "icon": icon,
                "change_url": change_url,
                "list_url": list_url,
                "is_late": locals().get("is_late", False),
                "late_display": locals().get("late_display", None),
            }
        )

    return statuses, totals, emp_image_url


# =====================================================================
# MAIN DASHBOARD VIEW (WIRES ALL HELPERS)
# =====================================================================
@staff_member_required
def attendance_dashboard_view(request):
    """
    Dashboard:
      - prev/next month navigation
      - import (csv/xlsx)
      - summary grid per employee
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


# =====================================================================
# FACE ATTENDANCE API HELPERS
# =====================================================================
def debug_request_print(request):
    print("DEBUG METHOD:", request.method)
    print("DEBUG POST KEYS:", list(request.POST.keys()))
    print("DEBUG FILE KEYS:", list(request.FILES.keys()))


def load_image_from_request(image_file):
    from PIL import Image

    print("DEBUG: image_file name:", image_file.name, "size:", image_file.size)
    img = Image.open(image_file).convert("RGB")
    return img


def detect_face_and_encoding(img):
    import numpy as np
    import face_recognition

    img_np = np.array(img)
    print("DEBUG: image shape:", img_np.shape)

    face_locations = face_recognition.face_locations(img_np)
    print("DEBUG: num face_locations:", len(face_locations))

    if not face_locations:
        return None, None, "No face detected."

    encoding = face_recognition.face_encodings(img_np, face_locations)[0]
    return img_np, encoding, None


def load_known_encodings():
    import numpy as np

    employees_qs = Employee.objects.exclude(face_encoding__isnull=True).exclude(
        face_encoding=[]
    )
    print("DEBUG: employees with encoding:", employees_qs.count())

    known_encodings = []
    employees = []

    for emp in employees_qs:
        try:
            arr = np.array(emp.face_encoding, dtype="float32")
            if arr.shape == (128,):
                known_encodings.append(arr)
                employees.append(emp)
        except Exception as e:
            print(f"DEBUG: bad encoding for employee {emp.id}: {e}")
            continue

    return known_encodings, employees


def find_best_match(known_encodings, employees, encoding):
    import numpy as np
    import face_recognition

    if not known_encodings:
        print("DEBUG: NO KNOWN ENCODINGS IN DB")
        return None, "No employees with registered face encodings."

    matches = face_recognition.compare_faces(known_encodings, encoding, tolerance=0.5)
    distances = face_recognition.face_distance(known_encodings, encoding)
    print("DEBUG: matches:", matches)
    print("DEBUG: distances:", distances.tolist())

    if not any(matches):
        print("DEBUG: FACE NOT RECOGNIZED")
        return None, "Face not recognized."

    best_index = int(np.argmin(distances))
    employee = employees[best_index]
    print(
        "DEBUG: recognized employee:",
        employee.id,
        employee.employee_id,
        employee.name,
    )
    return employee, None


def mark_attendance(employee, device_id, image_file):
    now = dhaka_now()
    today = now.date()

    record, created = AttendanceRecord.objects.get_or_create(
        employee=employee,
        date=today,
    )
    print("DEBUG: AttendanceRecord pk:", record.pk, "created:", created)

    check_type = None
    display_text = None

    # rewind file pointer to reuse uploaded file
    try:
        image_file.seek(0)
    except Exception:
        pass

    if record.checkin_time is None:
        record.checkin_time = now
        record.checkin_image = image_file
        record.device_id = device_id or record.device_id
        check_type = "IN"
        display_text = f"Welcome {employee.name}"
        record.save()
        print("DEBUG: saved CHECK-IN for record", record.pk)

    elif record.checkout_time is None:
        record.checkout_time = now
        record.checkout_image = image_file
        record.device_id = device_id or record.device_id
        check_type = "OUT"
        display_text = f"Goodbye {employee.name}"
        record.save()
        print("DEBUG: saved CHECK-OUT for record", record.pk)

    else:
        check_type = "NONE"
        display_text = f"Attendance already completed today for {employee.name}."
        print("DEBUG: already had IN and OUT for this employee today")

    return check_type, display_text


# =====================================================================
# MAIN FACE ATTENDANCE API VIEW
# =====================================================================
@csrf_exempt
def face_attendance_api(request):
    debug_request_print(request)

    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    device_id = (request.POST.get("device_id") or "").strip()
    image_file = request.FILES.get("image")

    if not image_file:
        print("DEBUG: NO IMAGE FILE IN REQUEST")
        return JsonResponse(
            {"error": "Image file (field name 'image') is required."}, status=400
        )

    # Load libs once here to keep debug behavior
    try:
        img = load_image_from_request(image_file)
    except Exception as e:
        print("DEBUG: PIL failed to open image:", e)
        return JsonResponse({"error": "Could not read image."}, status=400)

    img_np, encoding, err = detect_face_and_encoding(img)
    if err:
        return JsonResponse({"error": err}, status=400)

    known_encodings, employees = load_known_encodings()
    employee, err = find_best_match(known_encodings, employees, encoding)
    if err == "No employees with registered face encodings.":
        return JsonResponse({"error": err}, status=500)
    if err == "Face not recognized.":
        return JsonResponse({"status": "unknown", "message": err}, status=404)

    check_type, display_text = mark_attendance(employee, device_id, image_file)

    return JsonResponse(
        {
            "status": "ok",
            "employee_id": employee.employee_id,
            "employee_name": employee.name,
            "check_type": check_type,
            "display_text": display_text,
        }
    )
