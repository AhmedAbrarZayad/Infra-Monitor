from django.urls import path

from .monitoring_views import InternalEnrollmentView, InstallerStatusView


app_name = "monitoring-internal"

urlpatterns = [
    path("enroll/", InternalEnrollmentView.as_view(), name="enroll"),
    path(
        "enrollments/<uuid:enrollment_id>/status/",
        InstallerStatusView.as_view(),
        name="enrollment-status",
    ),
]
