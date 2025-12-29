from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from attendance.views import attendance_dashboard_view, set_language_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("attendance-dashboard/", attendance_dashboard_view),
    path("i18n/", include("django.conf.urls.i18n")),  # Language switch endpoint
    path("set-lang/<str:lang>/", set_language_view, name="set_language"),
    path("", include("attendance.urls", namespace="attendance")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
