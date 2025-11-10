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
from .utils.salary_helpers import (
    get_employee_salary_summary,
    process_monthly_salary_adjustments,
)
from .models import SalaryAdjustment
from decimal import Decimal


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


@staff_member_required
def salary_management_view(request):
    """
    Salary management dashboard for bonuses and fines
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
    Monthly salary report showing final calculations
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

    # Calculate salary data for each employee
    salary_data = []
    total_base_salary = Decimal("0.00")
    total_bonuses = Decimal("0.00")
    total_fines = Decimal("0.00")
    total_final_salary = Decimal("0.00")

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

    departments = Employee.objects.values_list("department", flat=True).distinct()

    context = {
        "month": selected_month,
        "year": selected_year,
        "selected_department": selected_department,
        "salary_data": salary_data,
        "departments": departments,
        "months": list(range(1, 13)),
        "years": [selected_year - 1, selected_year, selected_year + 1],
        "totals": {
            "base_salary": total_base_salary,
            "bonuses": total_bonuses,
            "fines": total_fines,
            "final_salary": total_final_salary,
        },
        "month_name": datetime(selected_year, selected_month, 1).strftime("%B %Y"),
        "message": message,
    }

    return TemplateResponse(request, "admin/salary-report.html", context)
