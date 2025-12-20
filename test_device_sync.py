
import os
import django
import json
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'attendance_project.settings')
django.setup()

from attendance.models import Organization, Device, OrganizationSettings
from attendance.views import device_validate_api
from django.test import RequestFactory

def test_device_sync():
    print("Setting up test data...")
    # Create or get organization
    org, _ = Organization.objects.get_or_create(name="Test Org Sync", slug="test-org-sync")
    
    # Update settings
    settings_obj, _ = OrganizationSettings.objects.get_or_create(organization=org)
    settings_obj.liveness_threshold = 0.95
    settings_obj.timezone = "Europe/London"
    settings_obj.save()
    
    # Create device
    device_id = "test_sync_device_001"
    Device.objects.filter(device_id=device_id).delete()
    device = Device.objects.create(
        organization=org,
        device_id=device_id,
        device_name="Test Sync Device",
        is_active=True
    )
    
    # Mock request
    factory = RequestFactory()
    request = factory.get('/api/devices/validate/', {'device_id': device_id})
    
    print("Calling device_validate_api...")
    response = device_validate_api(request)
    
    if response.status_code == 200:
        data = json.loads(response.content)
        print("Response received.")
        
        if "organization_settings" in data:
            print("SUCCESS: 'organization_settings' found in response.")
            settings_resp = data["organization_settings"]
            print(f"Liveness Threshold: {settings_resp.get('liveness_threshold')} (Expected: 0.95)")
            print(f"Timezone: {settings_resp.get('timezone')} (Expected: Europe/London)")
            
            if settings_resp.get('liveness_threshold') == 0.95:
                print("VERIFIED: Settings match database values.")
            else:
                print("FAILED: Settings mismatch.")
        else:
            print("FAILED: 'organization_settings' key missing in response.")
    else:
        print(f"FAILED: API returned status {response.status_code}")
        print(response.content)

if __name__ == "__main__":
    test_device_sync()
