import re

from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Organization
from log.models import LogEntry
from servers.models import Servers, Service


def redact_metadata(metadata):
    secrets = ("password", "token", "secret", "authorization")
    return {
        str(key): "[REDACTED]" if any(secret in str(key).lower() for secret in secrets) else value
        for key, value in dict(metadata).items()
    }


def redact_message(message):
    return re.sub(
        r"(?i)(password|token|secret|authorization)\s*[:=]\s*\S+",
        r"\1=[REDACTED]",
        str(message),
    )


class LogBatchView(APIView):
    def post(self, request):
        if not request.user.is_staff:
            return Response({"detail": "Staff service credentials are required."}, status=403)
        entries = request.data.get("entries", [])
        if not isinstance(entries, list) or len(entries) > 1000:
            return Response({"entries": ["Provide a list of at most 1000 entries."]}, status=400)
        created = []
        for data in entries:
            organization = get_object_or_404(Organization, pk=data.get("organization_id"))
            server = (
                get_object_or_404(Servers, organization=organization, pk=data.get("server_id"))
                if data.get("server_id")
                else None
            )
            service = (
                get_object_or_404(
                    Service,
                    server_id__organization=organization,
                    pk=data.get("service_id"),
                )
                if data.get("service_id")
                else None
            )
            entry = LogEntry.objects.create(
                organization=organization,
                server_id=server,
                service_id=service,
                source=str(data.get("source", ""))[:255],
                log_level=str(data.get("level", "INFO"))[:32],
                message=redact_message(data.get("message", "")),
                metadata=redact_metadata(data.get("metadata", {})),
                logged_at=parse_datetime(data.get("logged_at", "")) or timezone.now(),
            )
            created.append(str(entry.log_id))
        return Response({"created": created}, status=201)
