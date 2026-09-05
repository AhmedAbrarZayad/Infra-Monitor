from django.urls import path

from dashboard.views import AnalyticsView, OverviewView

app_name = "dashboard"
urlpatterns = [
    path("overview/", OverviewView.as_view(), name="overview"),
    path("analytics/", AnalyticsView.as_view(), name="analytics"),
]
