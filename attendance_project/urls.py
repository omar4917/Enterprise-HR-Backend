from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include, re_path
from django.views.static import serve
from attendance.views import attendance_dashboard_view, set_language_view
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from django.views.generic import RedirectView

urlpatterns = [
    # Swagger / OpenAPI Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),

    path("admin/", RedirectView.as_view(url='/', permanent=False)),
    path("admin", RedirectView.as_view(url='/', permanent=False)),
    path("attendance-dashboard/", attendance_dashboard_view),
    path("i18n/", include("django.conf.urls.i18n")),  # Language switch endpoint
    path("set-lang/<str:lang>/", set_language_view, name="set_language"),
    path("", include("attendance.urls", namespace="attendance")),
    path("", admin.site.urls),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
