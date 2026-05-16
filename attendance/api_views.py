"""
DRF ViewSets for the Enterprise HR Backend.

These replace the legacy function-based views with clean, DRF-powered
class-based ViewSets. Custom business logic (enrollment, check-in, etc.)
is exposed via @action decorators.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter

from .models import (
    Organization, Employee, Shift, AttendanceRecord, Device,
    OrganizationUser, OrganizationSettings, BulkHoliday,
    IntegrationSetting, VoiceSetting, TextMessageSetting, ContextSetting,
    SalaryStatistic, SalaryStatisticDefault, SubscriptionPlan, AuditLog,
    LiveFeedImage, ModeratorLabel,
)
from .serializers import (
    OrganizationSerializer, EmployeeSerializer, EmployeeListSerializer,
    ShiftSerializer, AttendanceRecordSerializer, DeviceSerializer,
    OrganizationUserSerializer, OrganizationSettingsSerializer,
    BulkHolidaySerializer, IntegrationSettingSerializer,
    VoiceSettingSerializer, TextMessageSettingSerializer, ContextSettingSerializer,
    SalaryStatisticSerializer, SalaryStatisticDefaultSerializer,
    SubscriptionPlanSerializer, AuditLogSerializer,
    LiveFeedImageSerializer, ModeratorLabelSerializer,
)
from .permissions import (
    IsSuperAdmin, IsOrgAdmin, IsOrgMember, IsOrgAdminOrReadOnly,
    OrganizationIsolationMixin, get_rbac_info, SUPER_ROLES,
)


# =============================================================================
# ORGANIZATION
# =============================================================================

@extend_schema_view(
    list=extend_schema(summary="List all organizations"),
    retrieve=extend_schema(summary="Get organization details"),
    create=extend_schema(summary="Create a new organization"),
    update=extend_schema(summary="Update an organization"),
    destroy=extend_schema(summary="Delete an organization"),
)
class OrganizationViewSet(viewsets.ModelViewSet):
    """
    CRUD for Organizations. Super admins see all; org users see only theirs.
    """
    queryset = Organization.objects.all().order_by('name')
    serializer_class = OrganizationSerializer
    permission_classes = [IsOrgAdminOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        info = get_rbac_info(self.request)
        if info['role'] in SUPER_ROLES:
            return qs
        org_id = info.get('org_id')
        if org_id:
            return qs.filter(id=org_id)
        return qs.none()

    @action(detail=True, methods=['get'], url_path='stats')
    def stats(self, request, pk=None):
        """Get statistics for a specific organization."""
        org = self.get_object()
        return Response({
            'id': org.id,
            'name': org.name,
            'employee_count': org.employee_count(),
            'device_count': org.device_count(),
            'is_at_employee_limit': org.is_at_employee_limit(),
            'is_at_device_limit': org.is_at_device_limit(),
            'max_employees': org.max_employees,
            'max_devices': org.max_devices,
        })


# =============================================================================
# EMPLOYEE
# =============================================================================

@extend_schema_view(
    list=extend_schema(summary="List employees", parameters=[
        OpenApiParameter('organization_id', int, description='Filter by org'),
        OpenApiParameter('department', str, description='Filter by department'),
        OpenApiParameter('is_active', bool, description='Filter active/inactive'),
    ]),
    retrieve=extend_schema(summary="Get employee details"),
    create=extend_schema(summary="Create/enroll an employee"),
)
class EmployeeViewSet(OrganizationIsolationMixin, viewsets.ModelViewSet):
    """
    CRUD for Employees with organization isolation.
    """
    queryset = Employee.objects.select_related('organization').all()
    permission_classes = [IsOrgAdminOrReadOnly]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_serializer_class(self):
        if self.action == 'list':
            return EmployeeListSerializer
        return EmployeeSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        # Additional filters
        dept = self.request.query_params.get('department')
        if dept:
            qs = qs.filter(department=dept)
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() in ('true', '1', 'yes'))
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(name__icontains=search) |
                Q(employee_id__icontains=search) |
                Q(department__icontains=search)
            )
        return qs.order_by('employee_id')


# =============================================================================
# SHIFT
# =============================================================================

@extend_schema_view(
    list=extend_schema(summary="List all shifts"),
    create=extend_schema(summary="Create a new shift"),
)
class ShiftViewSet(OrganizationIsolationMixin, viewsets.ModelViewSet):
    """CRUD for Shifts with organization isolation."""
    queryset = Shift.objects.all().order_by('name')
    serializer_class = ShiftSerializer
    permission_classes = [IsOrgAdminOrReadOnly]


# =============================================================================
# ATTENDANCE
# =============================================================================

@extend_schema_view(
    list=extend_schema(summary="List attendance records", parameters=[
        OpenApiParameter('date', str, description='Filter by date (YYYY-MM-DD)'),
        OpenApiParameter('status', str, description='Filter by status'),
        OpenApiParameter('employee_id', str, description='Filter by employee ID'),
    ]),
)
class AttendanceRecordViewSet(OrganizationIsolationMixin, viewsets.ModelViewSet):
    """
    CRUD for AttendanceRecords with organization isolation.
    """
    queryset = AttendanceRecord.objects.select_related(
        'employee', 'shift', 'organization'
    ).order_by('-date', '-checkin_time')
    serializer_class = AttendanceRecordSerializer
    permission_classes = [IsOrgAdminOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        # Date filter
        date_filter = self.request.query_params.get('date')
        if date_filter:
            qs = qs.filter(date=date_filter)
        # Status filter
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        # Employee filter
        emp_id = self.request.query_params.get('employee_id')
        if emp_id:
            qs = qs.filter(employee__employee_id=emp_id)
        # Month/Year filter
        month = self.request.query_params.get('month')
        year = self.request.query_params.get('year')
        if month and year:
            qs = qs.filter(date__month=month, date__year=year)
        return qs


# =============================================================================
# DEVICE
# =============================================================================

@extend_schema_view(
    list=extend_schema(summary="List all devices"),
    create=extend_schema(summary="Register a new device"),
)
class DeviceViewSet(OrganizationIsolationMixin, viewsets.ModelViewSet):
    """CRUD for Devices with organization isolation."""
    queryset = Device.objects.select_related('organization').all().order_by('device_name')
    serializer_class = DeviceSerializer
    permission_classes = [IsOrgAdminOrReadOnly]

    @action(detail=False, methods=['post'], url_path='validate')
    def validate_device(self, request):
        """Validate a device_id and return its organization."""
        device_id = request.data.get('device_id')
        if not device_id:
            return Response({'error': 'device_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            device = Device.objects.select_related('organization').get(device_id=device_id, is_active=True)
            device.update_last_seen()
            return Response({
                'valid': True,
                'device_id': device.device_id,
                'device_name': device.device_name,
                'organization_id': device.organization_id,
                'organization_name': device.organization.name,
            })
        except Device.DoesNotExist:
            return Response({'valid': False, 'error': 'Device not found or inactive'}, status=status.HTTP_404_NOT_FOUND)


# =============================================================================
# SETTINGS (Singleton pattern via get_solo)
# =============================================================================

class SingletonViewSet(viewsets.ViewSet):
    """
    Base ViewSet for singleton settings models (IntegrationSetting, VoiceSetting, etc.).
    Override `model_class` and `serializer_class` in subclasses.
    """
    model_class = None
    serializer_class = None
    permission_classes = [IsOrgAdminOrReadOnly]

    def list(self, request):
        obj = self.model_class.get_solo()
        serializer = self.serializer_class(obj)
        return Response(serializer.data)

    def create(self, request):
        obj = self.model_class.get_solo()
        serializer = self.serializer_class(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class IntegrationSettingViewSet(SingletonViewSet):
    model_class = IntegrationSetting
    serializer_class = IntegrationSettingSerializer


class VoiceSettingViewSet(SingletonViewSet):
    model_class = VoiceSetting
    serializer_class = VoiceSettingSerializer


class TextMessageSettingViewSet(SingletonViewSet):
    model_class = TextMessageSetting
    serializer_class = TextMessageSettingSerializer


class ContextSettingViewSet(SingletonViewSet):
    model_class = ContextSetting
    serializer_class = ContextSettingSerializer


# =============================================================================
# SALARY
# =============================================================================

@extend_schema_view(
    list=extend_schema(summary="List salary statistics", parameters=[
        OpenApiParameter('month', int, description='Filter by month'),
        OpenApiParameter('year', int, description='Filter by year'),
    ]),
)
class SalaryStatisticViewSet(OrganizationIsolationMixin, viewsets.ModelViewSet):
    """CRUD for SalaryStatistic records."""
    queryset = SalaryStatistic.objects.select_related('employee').order_by('-year', '-month')
    serializer_class = SalaryStatisticSerializer
    permission_classes = [IsOrgAdminOrReadOnly]
    org_field = 'employee__organization'

    def get_queryset(self):
        qs = super().get_queryset()
        month = self.request.query_params.get('month')
        year = self.request.query_params.get('year')
        if month:
            qs = qs.filter(month=int(month))
        if year:
            qs = qs.filter(year=int(year))
        return qs


class SalaryStatisticDefaultViewSet(SingletonViewSet):
    model_class = SalaryStatisticDefault
    serializer_class = SalaryStatisticDefaultSerializer


# =============================================================================
# HOLIDAYS
# =============================================================================

@extend_schema_view(
    list=extend_schema(summary="List holidays"),
    create=extend_schema(summary="Create a holiday"),
)
class BulkHolidayViewSet(OrganizationIsolationMixin, viewsets.ModelViewSet):
    """CRUD for BulkHoliday records."""
    queryset = BulkHoliday.objects.all().order_by('-created_at')
    serializer_class = BulkHolidaySerializer
    permission_classes = [IsOrgAdminOrReadOnly]


# =============================================================================
# SAAS: SUBSCRIPTION PLANS & AUDIT LOGS
# =============================================================================

@extend_schema_view(
    list=extend_schema(summary="List subscription plans"),
)
class SubscriptionPlanViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only access to subscription plans."""
    queryset = SubscriptionPlan.objects.filter(is_active=True).order_by('price_monthly')
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [IsOrgMember]


@extend_schema_view(
    list=extend_schema(summary="List audit logs"),
)
class AuditLogViewSet(OrganizationIsolationMixin, viewsets.ReadOnlyModelViewSet):
    """Read-only access to audit logs with organization isolation."""
    queryset = AuditLog.objects.all().order_by('-timestamp')
    serializer_class = AuditLogSerializer
    permission_classes = [IsOrgAdmin]


# =============================================================================
# ORG USERS
# =============================================================================

@extend_schema_view(
    list=extend_schema(summary="List organization users"),
    create=extend_schema(summary="Add a user to an organization"),
)
class OrganizationUserViewSet(viewsets.ModelViewSet):
    """CRUD for OrganizationUser associations."""
    queryset = OrganizationUser.objects.select_related('user', 'organization').all()
    serializer_class = OrganizationUserSerializer
    permission_classes = [IsOrgAdmin]

    def get_queryset(self):
        qs = super().get_queryset()
        info = get_rbac_info(self.request)
        if info['role'] in SUPER_ROLES:
            return qs
        org_id = info.get('org_id')
        if org_id:
            return qs.filter(organization_id=org_id)
        return qs.none()


# =============================================================================
# LIVE FEED
# =============================================================================

class LiveFeedImageViewSet(OrganizationIsolationMixin, viewsets.ModelViewSet):
    """CRUD for live feed images."""
    queryset = LiveFeedImage.objects.select_related('employee').order_by('-captured_at')
    serializer_class = LiveFeedImageSerializer
    permission_classes = [IsOrgMember]
    org_field = 'organization'


# =============================================================================
# MODERATOR LABELS
# =============================================================================

class ModeratorLabelViewSet(viewsets.ModelViewSet):
    """CRUD for moderator label overrides."""
    queryset = ModeratorLabel.objects.all().order_by('key')
    serializer_class = ModeratorLabelSerializer
    permission_classes = [IsOrgAdmin]
