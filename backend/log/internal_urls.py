from django.urls import path

from log.views import LogBatchView

app_name = "internal-logs"
urlpatterns = [path("batches/", LogBatchView.as_view(), name="batch-create")]
