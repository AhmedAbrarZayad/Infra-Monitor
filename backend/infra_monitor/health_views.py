from django.db import connection
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from servers.services import VictoriaMetricsQueryAdapter


class LiveView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"status": "ok"})


class ReadyView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return Response({"status": "ready", "database": "ok"})
        except Exception:
            return Response({"status": "not_ready"}, status=503)


class DependencyHealthView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        telemetry = "ok" if VictoriaMetricsQueryAdapter().healthy() else "unavailable"
        return Response(
            {
                "database": "ok",
                "telemetry": telemetry,
                "ml": "not_configured",
                "gemini": "not_configured",
            }
        )


class WorkerHealthView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        return Response({"status": "not_configured", "workers": []})
