from django.urls import path

from ml_model.views import InternalDetectionView

app_name = "internal-ml"
urlpatterns = [
    path("detections/", InternalDetectionView.as_view(), name="detections"),
]
