# seed_logic.py (place next to manage.py)

import os
import django

# Replace 'yourproject.settings' with the settings module used by your project.
# If you don't know it, open manage.py and copy the value of DJANGO_SETTINGS_MODULE there.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "attendance_project.settings")

django.setup()

# --- below this line keep the rest of your script unchanged ---
from attendance.models import SeasonProfile, LogicSettings

SeasonProfile.objects.get_or_create(
    name="Summer",
    defaults={
        "shift_start": "09:00",
        "shift_end": "18:00",
        "present_hours": 8,
        "half_day_hours": 4,
        "late_grace_minutes": 1,
        "enable_late_status": True,
    },
)

SeasonProfile.objects.get_or_create(
    name="Winter",
    defaults={
        "shift_start": "09:00",
        "shift_end": "18:00",
        "present_hours": 8,
        "half_day_hours": 5,
        "late_grace_minutes": 1,
        "enable_late_status": True,
    },
)

s = LogicSettings.get_solo()
s.active_season = SeasonProfile.objects.filter(name="Winter").first()
s.save()

print(
    "Seed complete:",
    SeasonProfile.objects.count(),
    "profiles; active:",
    s.active_season,
)
