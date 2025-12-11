import os
import django
import random
from datetime import datetime, timedelta
import sys

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'attendance_project.settings')
django.setup()

from attendance.models import Employee, LiveFeedImage
from django.utils import timezone

def create_dummy_livefeed():
    employees = Employee.objects.all()
    if not employees.exists():
        print("No employees found. Please create employees first.")
        return

    print(f"Found {employees.count()} employees. Generating livefeed images...")

    # Create a dummy image file if it doesn't exist
    dummy_image_path = 'media/livefeed/dummy.jpg'
    os.makedirs(os.path.dirname(dummy_image_path), exist_ok=True)
    
    # Create a simple colored square as a dummy image if not exists
    if not os.path.exists(dummy_image_path):
        from PIL import Image
        img = Image.new('RGB', (100, 100), color = (73, 109, 137))
        img.save(dummy_image_path)

    # Generate records for the last 3 days
    for i in range(3):
        date = timezone.now() - timedelta(days=i)
        for emp in employees:
            # 50% chance to have livefeed for a day
            if random.choice([True, False]):
                # Generate 1-3 images per day
                for _ in range(random.randint(1, 3)):
                    timestamp = date.replace(hour=random.randint(9, 18), minute=random.randint(0, 59))
                    
                    LiveFeedImage.objects.create(
                        employee=emp,
                        image='livefeed/dummy.jpg',
                        captured_at=timestamp
                    )
                    print(f"Created livefeed for {emp.name} at {timestamp}")

    print("Done generating dummy livefeed images.")

if __name__ == '__main__':
    create_dummy_livefeed()
