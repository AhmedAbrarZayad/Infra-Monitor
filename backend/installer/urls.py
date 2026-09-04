from django.urls import path

from .installer_view import InstallScriptChecksumView, InstallScriptView

app_name = "installer"

urlpatterns = [
    path("install.sh", InstallScriptView.as_view(), name="installer-script-download"),
    path("install.sh.sha256", InstallScriptChecksumView.as_view(), name="installer-script-checksum"),
]
