"""
Script to populate all organization fields with realistic dummy data.
Run with: python populate_org_info.py
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'attendance_project.settings')
django.setup()

from attendance.models import Organization

# Realistic data for each organization
ORG_DATA = {
    "Default Organization": {
        "address": "123 Main Street, Floor 5, Dhaka 1205, Bangladesh",
        "phone": "+880-2-9876543",
        "email": "info@defaultorg.com",
        "website": "https://www.defaultorg.com",
        "founder": "Mohammad Rahman",
    },
    "Digital Media Agency": {
        "address": "45 Creative Plaza, Gulshan-2, Dhaka 1212, Bangladesh",
        "phone": "+880-2-8823456",
        "email": "hello@digitalmedia.agency",
        "website": "https://www.digitalmedia.agency",
        "founder": "Sarah Ahmed",
    },
    "Global Trading Co.": {
        "address": "78 Commerce Tower, Motijheel, Dhaka 1000, Bangladesh",
        "phone": "+880-2-7712345",
        "email": "trade@globaltrading.co",
        "website": "https://www.globaltrading.co",
        "founder": "Abdul Karim",
    },
    "Healthcare Plus Hospital": {
        "address": "200 Medical Center Road, Dhanmondi, Dhaka 1209, Bangladesh",
        "phone": "+880-2-9123456",
        "email": "care@healthcareplus.hospital",
        "website": "https://www.healthcareplus.hospital",
        "founder": "Dr. Fatima Begum",
    },
    "PHP Settings Org": {
        "address": "55 Tech Park, Banani, Dhaka 1213, Bangladesh",
        "phone": "+880-2-8834567",
        "email": "admin@phpsettings.org",
        "website": "https://www.phpsettings.org",
        "founder": "Rashed Khan",
    },
    "Sunrise Garments": {
        "address": "Industrial Zone-3, Gazipur 1700, Bangladesh",
        "phone": "+880-2-9234567",
        "email": "export@sunrisegarments.com",
        "website": "https://www.sunrisegarments.com",
        "founder": "Nurul Islam",
    },
    "Tech Solutions Ltd": {
        "address": "IT Tower, Block-A, Uttara, Dhaka 1230, Bangladesh",
        "phone": "+880-2-8945678",
        "email": "info@techsolutions.ltd",
        "website": "https://www.techsolutions.ltd",
        "founder": "Tanvir Hossain",
    },
    "Test Org Sync": {
        "address": "99 Test Avenue, Mirpur-10, Dhaka 1216, Bangladesh",
        "phone": "+880-2-9056789",
        "email": "sync@testorg.io",
        "website": "https://www.testorg.io",
        "founder": "Test Admin",
    },
}

def run():
    orgs = Organization.objects.all()
    count = 0
    for org in orgs:
        data = ORG_DATA.get(org.name, {})
        if data:
            org.address = data.get("address", org.address)
            org.phone = data.get("phone", org.phone)
            org.email = data.get("email", org.email)
            org.website = data.get("website", org.website)
            org.founder = data.get("founder", org.founder)
            org.save()
            count += 1
            print(f"Updated: {org.name}")
            print(f"  Address: {org.address}")
            print(f"  Phone: {org.phone}")
            print(f"  Email: {org.email}")
            print(f"  Website: {org.website}")
            print(f"  Founder: {org.founder}")
            print(f"  TIN: {org.tin}")
            print(f"  BIN: {org.bin}")
            print()
        else:
            print(f"Skipped (no data defined): {org.name}")
    
    print(f"\nTotal: Updated {count} organizations with complete info.")

if __name__ == "__main__":
    run()
