"""
Script to assign logos to all organizations.
Run with: python assign_org_logos.py
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'attendance_project.settings')
django.setup()

from attendance.models import Organization

# Map organization slugs to logo files
LOGO_MAP = {
    "default": "org_logos/default.png",
    "digital-media": "org_logos/digital-media.png",
    "global-trading": "org_logos/global-trading.png",
    "healthcare-plus": "org_logos/healthcare-plus.png",
    "tech-solutions": "org_logos/tech-solutions.png",
    "sunrise-garments": "org_logos/sunrise-garments.png",
    "php-org-settings": "org_logos/default.png",  # Use default logo
    "test-org-sync": "org_logos/default.png",  # Use default logo
}

def run():
    orgs = Organization.objects.all()
    count = 0
    for org in orgs:
        logo_path = LOGO_MAP.get(org.slug)
        if logo_path:
            org.logo = logo_path
            org.save()
            count += 1
            print(f"Assigned logo to: {org.name} -> {logo_path}")
        else:
            print(f"No logo defined for: {org.name} (slug: {org.slug})")
    
    print(f"\nTotal: Assigned logos to {count} organizations.")

if __name__ == "__main__":
    run()
