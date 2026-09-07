from django.urls import path

from .views import DeviceRegistrationView

urlpatterns = [
    path("<uuid:installation_id>/", DeviceRegistrationView.as_view(), name="device-registration"),
]
