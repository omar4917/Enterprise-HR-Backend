from .models import AttendanceRecord
from .models import dhaka_now  # or timezone.now if you prefer


def register_punch(
    employee, direction, punch_time=None, image_file=None, filename="face.jpg"
):
    """
    direction: "IN" or "OUT"
    punch_time: datetime
    image_file: ContentFile or InMemoryUploadedFile
    """
    if punch_time is None:
        punch_time = dhaka_now()

    record, _ = AttendanceRecord.objects.get_or_create(
        employee=employee,
        date=punch_time.date(),
    )

    if direction == "IN":
        if record.checkin_time is None or punch_time < record.checkin_time:
            record.checkin_time = punch_time
            if image_file:
                record.checkin_image.save(filename, image_file, save=False)

    elif direction == "OUT":
        if record.checkout_time is None or punch_time > record.checkout_time:
            record.checkout_time = punch_time
            if image_file:
                record.checkout_image.save(filename, image_file, save=False)

    record.save()
    return record
