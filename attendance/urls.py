
from django.urls import path
from . import views

urlpatterns = [
    path(
        "api/face-attendance/",
        views.face_attendance_api,
        name="face_attendance_api",
    ),
]
