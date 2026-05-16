"""
DRF Permission classes replacing the legacy check_rbac() utility.

These read custom HTTP headers (X-User-Role, X-Organization-Id) set by the
PHP dashboard / API clients to enforce multi-tenant RBAC.
"""

from rest_framework.permissions import BasePermission

# Roles that bypass all organization isolation
SUPER_ROLES = ('super_admin', 'shadow_admin')
ADMIN_ROLES = ('super_admin', 'shadow_admin', 'org_main_admin', 'org_admin')
ALL_ROLES = ('super_admin', 'shadow_admin', 'org_main_admin', 'org_admin', 'org_viewer')


def get_rbac_info(request):
    """Extract RBAC headers from request. Returns dict with role, email, org_id."""
    return {
        'role': request.headers.get('X-User-Role', 'org_viewer'),
        'email': request.headers.get('X-User-Email', 'unknown'),
        'org_id': request.headers.get('X-Organization-Id'),
        'user_name': request.headers.get('X-User-Name', ''),
    }


class IsSuperAdmin(BasePermission):
    """Allows access only to super_admin or shadow_admin roles."""
    message = "Super admin access required."

    def has_permission(self, request, view):
        info = get_rbac_info(request)
        return info['role'] in SUPER_ROLES


class IsOrgAdmin(BasePermission):
    """Allows access to org admins and above."""
    message = "Organization admin access required."

    def has_permission(self, request, view):
        info = get_rbac_info(request)
        return info['role'] in ADMIN_ROLES


class IsOrgMember(BasePermission):
    """Allows access to any authenticated org member (including viewers)."""
    message = "Organization membership required."

    def has_permission(self, request, view):
        info = get_rbac_info(request)
        return info['role'] in ALL_ROLES


class IsOrgAdminOrReadOnly(BasePermission):
    """
    Org admins+ can do anything.
    Viewers can only perform safe methods (GET, HEAD, OPTIONS).
    """
    message = "Write access requires org admin role."

    def has_permission(self, request, view):
        info = get_rbac_info(request)
        if info['role'] in ADMIN_ROLES:
            return True
        if request.method in ('GET', 'HEAD', 'OPTIONS') and info['role'] in ALL_ROLES:
            return True
        return False


class OrganizationIsolationMixin:
    """
    ViewSet mixin that auto-filters querysets by the X-Organization-Id header.
    Super admins see all data; org users only see their organization's data.

    Usage:
        class EmployeeViewSet(OrganizationIsolationMixin, ModelViewSet):
            queryset = Employee.objects.all()
            org_field = 'organization'  # FK field name on the model
    """
    org_field = 'organization'  # Override in subclass if needed

    def get_queryset(self):
        qs = super().get_queryset()
        info = get_rbac_info(self.request)

        if info['role'] in SUPER_ROLES:
            # Super admins can optionally filter by org_id query param
            org_id = self.request.query_params.get('organization_id')
            if org_id:
                qs = qs.filter(**{f'{self.org_field}_id': org_id})
            return qs

        # Non-super users MUST be scoped to their organization
        org_id = info.get('org_id')
        if org_id:
            qs = qs.filter(**{f'{self.org_field}_id': org_id})
        else:
            # No org context = no data (safety net)
            qs = qs.none()
        return qs
