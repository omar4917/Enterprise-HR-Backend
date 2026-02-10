"""
Assign random images from E:\Entertainmaint\Pics IU to all employees.
Run with: python manage.py shell < assign_images.py
"""
import os, random, shutil, glob
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "attendance_project.settings")
django.setup()

from attendance.models import Employee
from django.conf import settings

SOURCE_DIR = r"E:\Entertainmaint\Pics IU"
MEDIA_ROOT = settings.MEDIA_ROOT
DEST_DIR = os.path.join(MEDIA_ROOT, "employee_photos")
os.makedirs(DEST_DIR, exist_ok=True)

# Get all images
images = glob.glob(os.path.join(SOURCE_DIR, "*.jpg")) + \
         glob.glob(os.path.join(SOURCE_DIR, "*.jpeg")) + \
         glob.glob(os.path.join(SOURCE_DIR, "*.png")) + \
         glob.glob(os.path.join(SOURCE_DIR, "*.webp"))

print(f"Found {len(images)} images in source folder")

employees = Employee.objects.all()
selected = random.sample(images, min(len(employees), len(images)))

for i, emp in enumerate(employees):
    src = selected[i]
    ext = os.path.splitext(src)[1]
    filename = f"{emp.employee_id}{ext}"
    dest = os.path.join(DEST_DIR, filename)
    
    shutil.copy2(src, dest)
    
    emp.employee_image = f"employee_photos/{filename}"
    emp.save(update_fields=["employee_image"])
    
    print(f"  [OK] {emp.employee_id} - {emp.name} <- {os.path.basename(src)}")

print(f"\nDone! Assigned images to {len(employees)} employees.")
