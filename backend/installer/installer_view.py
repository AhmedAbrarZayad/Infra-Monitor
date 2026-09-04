import hashlib
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, HttpResponse
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


def _script_path():
    return Path(settings.BASE_DIR) / "installer" / "install.sh"


class InstallScriptView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        script_path = _script_path()
        if not script_path.exists():
            return Response({"detail": "Installer not found."}, status=status.HTTP_404_NOT_FOUND)
        response = FileResponse(script_path.open("rb"), content_type="text/x-shellscript")
        response["Content-Disposition"] = 'attachment; filename="install.sh"'
        response["Cache-Control"] = "public, max-age=300"
        return response


class InstallScriptChecksumView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        script_path = _script_path()
        if not script_path.exists():
            return Response({"detail": "Installer not found."}, status=status.HTTP_404_NOT_FOUND)
        sha256_hash = hashlib.sha256()
        with script_path.open("rb") as script:
            for byte_block in iter(lambda: script.read(65536), b""):
                sha256_hash.update(byte_block)
        response = HttpResponse(
            f"{sha256_hash.hexdigest()}  install.sh\n",
            content_type="text/plain",
        )
        response["Cache-Control"] = "public, max-age=300"
        return response
