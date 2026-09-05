import secrets

from django.conf import settings
from django.db import transaction
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Organization
from ml_model.models import AnomalyDetection
from ml_model.presenters import present_anomaly
from ml_model.serializers import InternalDetectionSerializer
from servers.models import Servers, Service


class InternalDetectionView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @staticmethod
    def _authorized(request):
        expected = settings.ML_SERVICE_TOKEN
        header = request.headers.get("Authorization", "")
        scheme, separator, supplied = header.partition(" ")
        return bool(
            expected
            and separator
            and scheme == "Bearer"
            and supplied
            and secrets.compare_digest(supplied, expected)
        )

    def post(self, request):
        if not self._authorized(request):
            return Response(
                {"detail": "Invalid ML service token."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        serializer = InternalDetectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            organization = Organization.objects.get(pk=data["organization_id"])
            server = Servers.objects.get(pk=data["server_id"], organization=organization)
            service = Service.objects.get(pk=data["service_id"], server_id=server)
        except (Organization.DoesNotExist, Servers.DoesNotExist, Service.DoesNotExist):
            return Response(
                {"detail": "Organization, server, and service must belong together."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        defaults = {
            "organization": organization,
            "server_id": server,
            "is_anomaly": data["is_anomaly"],
            "anomaly_score": data["anomaly_score"],
            "confidence_score": data["confidence_score"],
            "feature_values": data["feature_values"],
        }
        with transaction.atomic():
            detection, created = AnomalyDetection.objects.update_or_create(
                service_id=service,
                window_started_at=data["window_started_at"],
                window_ended_at=data["window_ended_at"],
                model_version=data["model_version"],
                defaults=defaults,
            )

        return Response(
            present_anomaly(detection),
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
