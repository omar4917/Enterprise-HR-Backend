from django.core.management.base import BaseCommand
from attendance.models import Employee
from django.core.files import File
import os

class Command(BaseCommand):
    help = 'Loads dummy images for testing'

    def handle(self, *args, **kwargs):
        images = [
            r"C:/Users/Dlwlrma/.gemini/antigravity/brain/ee5673eb-6b00-4669-8dc4-24346b5a9950/uploaded_image_0_1766568222408.png",
            r"C:/Users/Dlwlrma/.gemini/antigravity/brain/ee5673eb-6b00-4669-8dc4-24346b5a9950/uploaded_image_1_1766568222408.png",
            r"C:/Users/Dlwlrma/.gemini/antigravity/brain/ee5673eb-6b00-4669-8dc4-24346b5a9950/uploaded_image_2_1766568222408.png"
        ]

        employees = Employee.objects.all().order_by('employee_id')[:3]
        
        self.stdout.write(f"Found {len(employees)} employees to update...")

        for i, emp in enumerate(employees):
            if i >= len(images):
                break
            
            img_path = images[i]
            if os.path.exists(img_path):
                self.stdout.write(f"Assigning {img_path} to {emp.name} ({emp.employee_id})")
                with open(img_path, 'rb') as f:
                    emp.employee_image.save(os.path.basename(img_path), File(f), save=True)
            else:
                self.stdout.write(self.style.WARNING(f"Image not found: {img_path}"))
        
        self.stdout.write(self.style.SUCCESS('Successfully loaded dummy images'))
