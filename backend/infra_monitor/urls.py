"""
URL configuration for infra_monitor project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/organizations/", include("accounts.organization_urls")),
    path("api/organizations/<uuid:organization_id>/", include("infra_monitor.operational_urls")),
]

from infra_monitor.operational_views import DependencyHealthView, LiveView, LogBatchView, PreferencesView, ReadyView, WorkerHealthView
urlpatterns += [
    path("api/auth/me/preferences/", PreferencesView.as_view()),
    path("api/health/live/", LiveView.as_view()), path("api/health/ready/", ReadyView.as_view()),
    path("api/internal/health/dependencies/", DependencyHealthView.as_view()), path("api/internal/health/workers/", WorkerHealthView.as_view()),
    path("api/internal/logs/batches/", LogBatchView.as_view()),
]
