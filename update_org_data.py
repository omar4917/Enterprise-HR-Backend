"""
Quick script to populate dummy TIN, BIN, and Founder for all organizations.
Run with: python manage.py runscript update_org_data
Or directly: python update_org_data.py
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'attendance_project.settings')
django.setup()

from attendance.models import Organization

def run():
    orgs = Organization.objects.all()
    count = 0
    for org in orgs:
        org.tin = f"TIN-{1000 + org.id}"
        org.bin = f"BIN-{2000 + org.id}"
        org.founder = "John Doe"
        org.save()
        count += 1
        print(f"Updated: {org.name} - TIN: {org.tin}, BIN: {org.bin}, Founder: {org.founder}")
    
    print(f"\nTotal: Updated {count} organizations with dummy TIN, BIN, and Founder.")

if __name__ == "__main__":
    run()
