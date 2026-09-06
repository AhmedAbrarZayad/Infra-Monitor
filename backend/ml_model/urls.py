from django.urls import path

from ml_model.views import (
    AnomalyAssignView,
    AnomalyAssignmentHistoryView,
    AnomalyDetailView,
    AnomalyListView,
    AnomalyResolveView,
)

app_name = "anomalies"
urlpatterns = [
    path("anomalies/", AnomalyListView.as_view(), name="list"),
    path("anomalies/<uuid:detection_id>/", AnomalyDetailView.as_view(), name="detail"),
    path(
        "anomalies/<uuid:detection_id>/assignment/",
        AnomalyAssignView.as_view(),
        name="assignment",
    ),
    path(
        "anomalies/<uuid:detection_id>/assignment-history/",
        AnomalyAssignmentHistoryView.as_view(),
        name="assignment-history",
    ),
    path(
        "anomalies/<uuid:detection_id>/resolve/",
        AnomalyResolveView.as_view(),
        name="resolve",
    ),
]
