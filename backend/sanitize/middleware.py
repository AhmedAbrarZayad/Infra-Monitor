"""Django middleware that captures metadata about every request arriving at
the Infra-Monitor platform API and stores it as a PLATFORM-source request log.

This gives the admin a separate panel to monitor the security of the
monitoring platform itself — distinct from the external server request logs
ingested via the Alloy agent.

The middleware is lightweight: it records metadata only (no request bodies)
and delegates classification to the async Celery pipeline.
"""

from __future__ import annotations

import logging
import time

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# Paths that should never be logged (health checks, metrics, static).
_SKIP_PREFIXES = (
    "/api/health",
    "/api/readiness",
    "/static/",
    "/favicon.ico",
)


class RequestShieldMiddleware:
    """Capture request metadata for platform self-monitoring.

    Inserted after AuthenticationMiddleware so ``request.user`` is available.
    Only active when the organization's ``ShieldConfig.platform_self_monitor``
    is enabled (or when no config exists, defaults to off to avoid noise
    during initial setup).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip non-API and health-check paths.
        if any(request.path.startswith(prefix) for prefix in _SKIP_PREFIXES):
            return self.get_response(request)

        start_time = time.monotonic()
        response = self.get_response(request)
        elapsed_ms = (time.monotonic() - start_time) * 1000

        # Fire-and-forget: record the request asynchronously.
        try:
            self._record(request, response, elapsed_ms)
        except Exception:
            # Never let middleware logging break an API response.
            logger.debug("RequestShieldMiddleware recording failed", exc_info=True)

        return response

    def _record(self, request, response, elapsed_ms):
        # Lazy import to avoid app-registry issues at startup.
        from sanitize.models import RequestLog

        # Determine organization from URL if possible.
        org_id = _extract_org_id(request.path)
        if org_id is None:
            return  # Can't attribute to an org — skip.

        source_ip = _get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        content_length = request.META.get("CONTENT_LENGTH")
        if content_length:
            try:
                content_length = int(content_length)
            except (ValueError, TypeError):
                content_length = None

        # Build a sanitized header digest (strip sensitive headers).
        headers_digest = {}
        for key, value in request.META.items():
            if key.startswith("HTTP_") and key not in (
                "HTTP_COOKIE",
                "HTTP_AUTHORIZATION",
                "HTTP_X_CSRFTOKEN",
            ):
                headers_digest[key[5:].lower().replace("_", "-")] = value[:200]

        from sanitize.features import extract_features, extract_threat_signals

        features = extract_features(
            method=request.method,
            path=request.path,
            query_string=request.META.get("QUERY_STRING", ""),
            status_code=response.status_code,
            user_agent=user_agent,
            content_length=content_length,
            response_time_ms=elapsed_ms,
            referer=request.META.get("HTTP_REFERER", ""),
            protocol=request.META.get("SERVER_PROTOCOL", ""),
            headers_digest=headers_digest,
        )
        threat_signals = extract_threat_signals(
            path=request.path,
            query_string=request.META.get("QUERY_STRING", ""),
            user_agent=user_agent,
        )

        RequestLog.objects.create(
            organization_id=org_id,
            server=None,
            timestamp=timezone.now(),
            source_ip=source_ip,
            method=request.method,
            path=request.path,
            query_string=request.META.get("QUERY_STRING", ""),
            status_code=response.status_code,
            user_agent=user_agent,
            content_length=content_length,
            response_time_ms=round(elapsed_ms, 2),
            referer=request.META.get("HTTP_REFERER", ""),
            protocol=request.META.get("SERVER_PROTOCOL", ""),
            headers_digest=headers_digest,
            source=RequestLog.Source.PLATFORM,
            feature_vector=features,
            threat_signals=threat_signals,
        )


def _get_client_ip(request):
    """Best-effort client IP extraction, respecting X-Forwarded-For."""
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "127.0.0.1")


def _extract_org_id(path):
    """Extract organization UUID from URL path.

    Expected pattern: /api/organizations/<uuid>/...
    """
    import re

    match = re.search(
        r"/api/organizations/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/",
        path,
        re.IGNORECASE,
    )
    return match.group(1) if match else None
