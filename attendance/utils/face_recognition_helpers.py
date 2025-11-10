from ..models import AttendanceRecord, Employee, dhaka_now


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