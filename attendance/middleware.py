"""
API Key Authentication Middleware for PHP Frontend.

Allows API endpoints to be accessed with:
- Authorization: Key <API_KEY>
- Or standard Basic Auth credentials
"""
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth import login


class APIKeyAuthMiddleware:
    """
    Middleware that authenticates requests using an API key.
    If Authorization header contains 'Key <API_KEY>', the request is treated as authenticated.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')

        # Check for API Key authentication
        if auth_header.startswith('Key '):
            api_key = auth_header[4:]  # Extract key after "Key "
            expected_key = getattr(settings, 'API_KEY', 'Key123')

            if api_key == expected_key:
                # API key is valid - set request.user to first superuser
                # This allows @staff_member_required decorated views to pass
                if not request.user.is_authenticated:
                    try:
                        admin_user = User.objects.filter(is_superuser=True).first()
                        if admin_user:
                            request.user = admin_user
                            # Don't create session, just set user for this request
                    except Exception:
                        pass

        return self.get_response(request)
