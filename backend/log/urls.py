from django.urls import path

from log.views import LogDetailView, LogListView

app_name = "logs"
urlpatterns = [
    path("logs/", LogListView.as_view(), name="list"),
    path("logs/<uuid:log_id>/", LogDetailView.as_view(), name="detail"),
]
