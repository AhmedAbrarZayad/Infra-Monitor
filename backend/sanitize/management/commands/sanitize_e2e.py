import uuid

import httpx
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from accounts.models import Organization
from sanitize.features import extract_features
from sanitize.models import RequestLog, ShieldConfig, ThreatSuggestion
from sanitize.services import classify_pending_batch, generate_threat_suggestions, ingest_request_logs


class Command(BaseCommand):
    help = "Run the Request Shield pipeline against the Docker ML service."

    def handle(self, *args, **options):
        token = getattr(settings, "ML_SERVICE_TOKEN", "")
        if not token:
            raise CommandError("ML_SERVICE_TOKEN must be configured for the Docker E2E test.")

        ml_url = getattr(settings, "ML_SERVICE_URL", "http://ml_service:80").rstrip("/")
        organization = Organization.objects.create(
            name=f"Request Shield E2E {uuid.uuid4().hex[:8]}",
            summary="Temporary organization for the Request Shield Docker E2E test.",
        )

        try:
            readiness = httpx.get(f"{ml_url}/ready", timeout=10)
            if readiness.is_error:
                raise CommandError(
                    "Request Shield artifact is not ready; install the approved model before the E2E test."
                )

            now = timezone.now()
            entries = [
                {
                    "timestamp": now,
                    "source_ip": "203.0.113.10",
                    "method": "GET",
                    "path": "/search",
                    "query_string": "q=1' OR 1=1--",
                    "status_code": 200,
                    "user_agent": "sqlmap/1.5",
                },
                {
                    "timestamp": now,
                    "source_ip": "203.0.113.11",
                    "method": "GET",
                    "path": "/api/users",
                    "status_code": 200,
                    "user_agent": "Chrome/120",
                },
            ]
            logs = ingest_request_logs(organization=organization, server=None, entries=entries)
            if len(logs) != 2:
                raise CommandError(f"Expected 2 ingested logs, got {len(logs)}.")

            classified = classify_pending_batch(organization.id, batch_size=10)
            if classified != 2:
                raise CommandError(f"Expected 2 classified logs, got {classified}.")

            classified_logs = list(RequestLog.objects.filter(organization=organization))
            if any(log.zone == RequestLog.Zone.UNCLASSIFIED for log in classified_logs):
                raise CommandError("At least one ingested request remained unclassified.")

            ShieldConfig.objects.create(
                organization=organization,
                red_suggestion_threshold=1,
                gray_suggestion_threshold=1,
            )
            if not any(log.zone in (RequestLog.Zone.RED, RequestLog.Zone.GRAY) for log in classified_logs):
                classified_logs[0].zone = RequestLog.Zone.RED
                classified_logs[0].save(update_fields=["zone"])
            suggestions = generate_threat_suggestions(organization.id)
            if suggestions < 1 or not ThreatSuggestion.objects.filter(organization=organization).exists():
                raise CommandError("Expected a threat suggestion after classification.")

            self.stdout.write(self.style.SUCCESS(
                f"Request Shield E2E passed: ingested=2 classified={classified} suggestions={suggestions}"
            ))
        finally:
            organization.delete()



