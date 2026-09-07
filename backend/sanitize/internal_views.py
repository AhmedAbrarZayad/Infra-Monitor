"""Views for the sanitize app — internal ingestion endpoints.

These are called by the Alloy agent on monitored servers, not by Flutter.
Authentication is via server credentials (same as the metrics write endpoint).
"""

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from installer.authentication import ServerCredentialAuthentication
from sanitize.serializers import RequestLogBatchSerializer
from sanitize.services import ingest_request_logs
from servers.models import Servers


class RequestLogIngestionView(APIView):
    """Receives batches of parsed access-log entries from the Alloy agent."""

    authentication_classes = [ServerCredentialAuthentication]
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RequestLogBatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        credential = request.auth
        server = credential.connection.server

        # Verify the reported server_id matches the authenticated server.
        if str(server.server_id) != str(data["server_id"]):
            return Response(
                {"detail": "server_id does not match authenticated server."},
                status=status.HTTP_403_FORBIDDEN,
            )

        logs = ingest_request_logs(
            organization=server.organization,
            server=server,
            entries=data["entries"],
            source="EXTERNAL",
        )

        return Response(
            {
                "accepted": len(logs),
                "server_id": str(server.server_id),
            },
            status=status.HTTP_201_CREATED,
        )
