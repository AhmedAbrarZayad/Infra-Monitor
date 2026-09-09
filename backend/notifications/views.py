import uuid

from django.db import transaction
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DeviceRegistration


class DeviceRegistrationView(APIView):
    def put(self, request, installation_id):
        token = str(request.data.get("token", "")).strip()
        if not token or len(token) > 4096:
            return Response({"token": ["A valid FCM token is required."]}, status=400)
        try:
            installation_id = uuid.UUID(str(installation_id))
        except ValueError:
            return Response({"installation_id": ["A valid UUID is required."]}, status=400)

        with transaction.atomic():
            DeviceRegistration.objects.filter(token=token).exclude(
                installation_id=installation_id
            ).delete()
            registration, _ = DeviceRegistration.objects.update_or_create(
                installation_id=installation_id,
                defaults={"user": request.user, "token": token, "active": True},
            )
        return Response(
            {
                "installation_id": registration.installation_id,
                "active": registration.active,
                "last_seen_at": registration.last_seen_at,
            }
        )

    def delete(self, request, installation_id):
        DeviceRegistration.objects.filter(
            installation_id=installation_id, user=request.user
        ).update(active=False)
        return Response(status=204)
