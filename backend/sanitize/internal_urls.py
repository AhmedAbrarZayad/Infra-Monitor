"""Internal (agent-facing) URL patterns for the Request Shield feature.

Included under /api/internal/request-logs/ in the root URL config.
"""

from django.urls import path

from sanitize.internal_views import RequestLogIngestionView

urlpatterns = [
    path("", RequestLogIngestionView.as_view(), name="shield-ingestion"),
]
