from django.views.decorators.csrf import csrf_exempt
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.template.response import TemplateResponse

from .models import Employee, get_active_shift
from .utils.dashboard_helpers import (
    get_dashboard_params,
    build_month_nav,
    build_days,
    get_employee_queryset,
    build_record_map,
    build_employee_row,
)
from .utils.import_helpers import handle_import, HAS_OPENPYXL
from .utils.face_recognition_helpers import (
    debug_request_print,
    load_image_from_request,
    detect_face_and_encoding,
    load_known_encodings,
    find_best_match,
    mark_attendance,
)


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