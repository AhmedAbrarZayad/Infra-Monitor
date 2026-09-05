from django.urls import path

from ml_model.views import AnomalyDetailView, AnomalyListView

app_name = "anomalies"
urlpatterns = [
    path("anomalies/", AnomalyListView.as_view(), name="list"),
    path("anomalies/<uuid:detection_id>/", AnomalyDetailView.as_view(), name="detail"),
]
