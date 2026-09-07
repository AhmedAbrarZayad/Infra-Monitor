"""Organization-scoped URL patterns for the Request Shield feature.

These are included under /api/organizations/<org_id>/ via the
organization_urls router.
"""

from django.urls import path

from sanitize.views import (
    RequestLogDetailView,
    RequestLogListView,
    RequestLogVerdictView,
    ShieldAnalyticsView,
    ShieldConfigView,
    ThreatSuggestionActionView,
    ThreatSuggestionListView,
)

urlpatterns = [
    # Analytics dashboard
    path(
        "request-shield/analytics/",
        ShieldAnalyticsView.as_view(),
        name="shield-analytics",
    ),
    # Request log browsing
    path(
        "request-shield/requests/",
        RequestLogListView.as_view(),
        name="shield-request-list",
    ),
    path(
        "request-shield/requests/<uuid:log_id>/",
        RequestLogDetailView.as_view(),
        name="shield-request-detail",
    ),
    path(
        "request-shield/requests/<uuid:log_id>/verdict/",
        RequestLogVerdictView.as_view(),
        name="shield-request-verdict",
    ),
    # Threat suggestions
    path(
        "request-shield/suggestions/",
        ThreatSuggestionListView.as_view(),
        name="shield-suggestion-list",
    ),
    path(
        "request-shield/suggestions/<uuid:suggestion_id>/action/",
        ThreatSuggestionActionView.as_view(),
        name="shield-suggestion-action",
    ),
    # Configuration
    path(
        "request-shield/config/",
        ShieldConfigView.as_view(),
        name="shield-config",
    ),
]
