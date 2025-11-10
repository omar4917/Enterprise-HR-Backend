import csv
import io
from datetime import datetime, date, timedelta

from ..models import AttendanceRecord, Employee

# Optional XLSX support
try:
    import openpyxl
    HAS_OPENPYXL = True
except Exception:
    HAS_OPENPYXL = False


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