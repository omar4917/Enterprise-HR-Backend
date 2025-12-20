
import os
import django
import json
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'attendance_project.settings')
django.setup()

from attendance.models import Organization, OrganizationSettings, ContextSetting, OrganizationUser
from attendance.views import context_settings_api
from django.test import RequestFactory
from django.contrib.auth.models import User

def test_context_settings_api():
    print("Setting up test data...")
    # Create or get organization
    org, _ = Organization.objects.get_or_create(name="PHP Settings Org", slug="php-org-settings")
    
    # Ensure settings exist
    settings_obj, _ = OrganizationSettings.objects.get_or_create(organization=org)
    settings_obj.liveness_threshold = 0.5 # Default check
    settings_obj.timezone = "Asia/Dhaka"
    settings_obj.save()
    
    # Create user for RBAC
    user, _ = User.objects.get_or_create(username="php_admin_user", email="phpadmin@example.com")
    
    # Create OrgUser
    org_user, _ = OrganizationUser.objects.get_or_create(user=user, organization=org, defaults={'role': 'org_admin'})
    org_user.role = 'org_admin'
    org_user.save()

    factory = RequestFactory()
    
    # --- TEST GET ---
    print("\n--- Testing GET ---")
    request = factory.get('/api/context-settings/')
    request.headers = {
        'X-Organization-Id': str(org.id),
        'X-User-Role': 'org_admin'
    }
    
    response = context_settings_api(request)
    if response.status_code == 200:
        data = json.loads(response.content)
        print("GET Response received.")
        print(f"Liveness: {data.get('liveness_threshold')} (Expected: 0.5)")
        print(f"Timezone: {data.get('timezone')} (Expected: Asia/Dhaka)")
        
        if data.get('liveness_threshold') == 0.5:
            print("GET Verified: Liveness matches.")
        else:
            print("GET Failed: Liveness mismatch.")
    else:
        print(f"GET Failed: Status {response.status_code}")

    # --- TEST POST (Update) ---
    print("\n--- Testing POST ---")
    payload = {
        "text_message_display": "1",
        "voice_message_active": "1", # Global
        "liveness_threshold": "0.99",
        "match_threshold": "0.88",
        "timezone": "Europe/Paris",
        "work_week_start": "1", # Monday
        "voice_enabled": "1",
        "default_voice_language": "fr",
        "email_on_late": "1"
    }
    
    request = factory.post(
        '/api/context-settings/', 
        data=json.dumps(payload), 
        content_type='application/json'
    )
    request.headers = {
        'X-Organization-Id': str(org.id),
        'X-User-Role': 'org_admin',
        'X-User-Email': 'phpadmin@example.com'
    }
    
    response = context_settings_api(request)
    if response.status_code == 200:
        print("POST Response received.")
        
        # Verify persistence
        settings_obj.refresh_from_db()
        print(f"New Liveness: {settings_obj.liveness_threshold} (Expected: 0.99)")
        print(f"New Timezone: {settings_obj.timezone} (Expected: Europe/Paris)")
        print(f"New Week Start: {settings_obj.work_week_start} (Expected: 1)")
        
        if settings_obj.liveness_threshold == 0.99 and settings_obj.work_week_start == 1:
             print("POST Verified: DB updated correctly.")
        else:
             print("POST Failed: DB mismatch.")
             
        # Verify Global context
        ctx = ContextSetting.get_solo()
        print(f"Global Voice Active: {ctx.voice_message_active} (Expected: True)")
    else:
        print(f"POST Failed: Status {response.status_code}")
        print(response.content)

if __name__ == "__main__":
    test_context_settings_api()
