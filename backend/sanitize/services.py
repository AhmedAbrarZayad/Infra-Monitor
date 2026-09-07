"""Core business logic for the Request Shield feature.

Functions here are called by views and Celery tasks. They encapsulate
ingestion, classification orchestration, and threat suggestion generation.
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import timedelta

import httpx
from django.conf import settings
from django.db.models import Count
from django.utils import timezone

from sanitize.features import FEATURE_NAMES, extract_features, extract_threat_signals
from sanitize.models import RequestLog, ShieldConfig, ThreatSuggestion

logger = logging.getLogger(__name__)


# ── Ingestion ───────────────────────────────────────────────────────


def ingest_request_logs(*, organization, server, entries, source="EXTERNAL"):
    """Bulk-create ``RequestLog`` rows from validated ingestion entries.

    Feature extraction is done eagerly so the classification task only needs
    to send the pre-computed vectors to the ML service.
    """
    now = timezone.now()
    logs = []
    for entry in entries:
        features = extract_features(
            method=entry["method"],
            path=entry["path"],
            query_string=entry.get("query_string", ""),
            status_code=entry.get("status_code"),
            user_agent=entry.get("user_agent", ""),
            content_length=entry.get("content_length"),
            response_time_ms=entry.get("response_time_ms"),
            referer=entry.get("referer", ""),
            protocol=entry.get("protocol", ""),
            headers_digest=entry.get("headers_digest", {}),
        )
        threat_signals = extract_threat_signals(
            path=entry["path"],
            query_string=entry.get("query_string", ""),
            user_agent=entry.get("user_agent", ""),
        )
        logs.append(
            RequestLog(
                organization=organization,
                server=server,
                timestamp=entry["timestamp"],
                source_ip=entry["source_ip"],
                method=entry["method"],
                path=entry["path"],
                query_string=entry.get("query_string", ""),
                status_code=entry.get("status_code"),
                user_agent=entry.get("user_agent", ""),
                content_length=entry.get("content_length"),
                response_time_ms=entry.get("response_time_ms"),
                referer=entry.get("referer", ""),
                protocol=entry.get("protocol", ""),
                headers_digest=entry.get("headers_digest", {}),
                source=source,
                feature_vector=features,
                threat_signals=threat_signals,
            )
        )
    return RequestLog.objects.bulk_create(logs) if logs else []


# ── Classification ──────────────────────────────────────────────────


def classify_pending_batch(organization_id, batch_size=100):
    """Send unclassified request logs to the ML service for zone classification.

    Returns the number of logs classified.
    """
    pending = (
        RequestLog.objects.filter(
            organization_id=organization_id,
            zone=RequestLog.Zone.UNCLASSIFIED,
            feature_vector__isnull=False,
        )
        .order_by("timestamp")[:batch_size]
    )
    pending = list(pending)
    if not pending:
        return 0

    vectors = [log.feature_vector for log in pending]
    log_ids = [str(log.id) for log in pending]

    ml_url = getattr(settings, "ML_SERVICE_URL", "http://ml_service:80").rstrip("/")
    ml_token = getattr(settings, "ML_SERVICE_TOKEN", "")
    timeout = getattr(settings, "ML_REQUEST_TIMEOUT_SECONDS", 30)

    try:
        response = httpx.post(
            f"{ml_url}/classify-requests",
            json={
                "feature_names": FEATURE_NAMES,
                "vectors": vectors,
            },
            headers={"Authorization": f"Bearer {ml_token}"},
            timeout=float(timeout),
        )
        response.raise_for_status()
        results = response.json()
    except (httpx.HTTPError, ValueError, KeyError):
        logger.exception(
            "ML service classification failed for org=%s batch=%d",
            organization_id,
            len(pending),
        )
        return 0

    now = timezone.now()
    classifications = results.get("classifications", [])
    classified = 0
    for log, classification in zip(pending, classifications):
        log.zone = classification.get("zone", RequestLog.Zone.UNCLASSIFIED)
        log.confidence = classification.get("confidence")
        log.classified_at = now
        log.classified_by = RequestLog.Classifier.ML_MODEL
        classified += 1

    RequestLog.objects.bulk_update(
        pending[:classified],
        fields=["zone", "confidence", "classified_at", "classified_by"],
    )
    return classified


# ── Gemini gray-zone escalation ─────────────────────────────────────


def _build_gemini_prompt(logs):
    """Build a Gemini prompt from a batch of GRAY-zone request logs."""
    entries = []
    for log in logs:
        entries.append(
            {
                "source_ip": log.source_ip,
                "method": log.method,
                "path": log.path,
                "query_string": log.query_string,
                "user_agent": log.user_agent,
                "status_code": log.status_code,
                "threat_signals": log.threat_signals,
            }
        )
    return (
        "You are a cybersecurity analyst reviewing HTTP requests flagged as "
        "suspicious (GRAY zone) by an ML classifier. For each request, decide "
        "whether it should be escalated to RED (malicious), kept as GRAY "
        "(still suspicious), or downgraded to GREEN (safe). Return a JSON "
        "array with one object per request: "
        '{"index": <0-based>, "zone": "RED"|"GRAY"|"GREEN", "reason": "brief explanation"}.\n\n'
        "Requests:\n" + json.dumps(entries, default=str)
    )


async def escalate_gray_to_gemini(organization_id, batch_size=20):
    """Send GRAY-zone requests to Gemini for deeper analysis.

    Updates their zone based on Gemini's response.
    """
    if not getattr(settings, "GEMINI_API_KEY", ""):
        return 0

    config = ShieldConfig.objects.filter(organization_id=organization_id).first()
    if config and not config.gemini_escalation:
        return 0

    gray_logs = list(
        RequestLog.objects.filter(
            organization_id=organization_id,
            zone=RequestLog.Zone.GRAY,
            classified_by=RequestLog.Classifier.ML_MODEL,
        )
        .order_by("timestamp")[:batch_size]
    )
    if not gray_logs:
        return 0

    from google import genai
    from google.genai import types

    prompt = _build_gemini_prompt(gray_logs)
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    try:
        response = await client.aio.models.generate_content(
            model=getattr(settings, "GEMINI_MODEL", "gemini-3.7-flash"),
            contents=[{"role": "user", "parts": [{"text": prompt}]}],
            config=types.GenerateContentConfig(
                system_instruction=(
                    "You are a cybersecurity threat classifier. Respond ONLY with "
                    "a valid JSON array. No markdown, no explanation outside the JSON."
                ),
                max_output_tokens=2048,
                response_mime_type="application/json",
            ),
        )
    except Exception:
        logger.exception("Gemini escalation failed for org=%s", organization_id)
        return 0
    finally:
        await client.aio.aclose()

    try:
        verdicts = json.loads(response.text)
    except (json.JSONDecodeError, AttributeError):
        logger.warning("Gemini returned unparseable response for org=%s", organization_id)
        return 0

    now = timezone.now()
    updated = 0
    for verdict in verdicts:
        idx = verdict.get("index")
        zone = verdict.get("zone", "").upper()
        if idx is None or idx >= len(gray_logs) or zone not in ("RED", "GRAY", "GREEN"):
            continue
        log = gray_logs[idx]
        log.zone = zone
        log.classified_at = now
        log.classified_by = RequestLog.Classifier.GEMINI
        updated += 1

    if updated:
        RequestLog.objects.bulk_update(
            gray_logs[:updated],
            fields=["zone", "classified_at", "classified_by"],
        )
    return updated


# ── Threat suggestion generation ────────────────────────────────────


def generate_threat_suggestions(organization_id):
    """Check for IPs exceeding zone thresholds and create suggestions.

    Returns the number of new suggestions created.
    """
    config = ShieldConfig.objects.filter(organization_id=organization_id).first()
    if config is None or not config.enabled:
        return 0

    now = timezone.now()
    window_start = now - timedelta(minutes=config.suggestion_window_minutes)

    created = 0
    for zone, threshold in [
        (RequestLog.Zone.RED, config.red_suggestion_threshold),
        (RequestLog.Zone.GRAY, config.gray_suggestion_threshold),
    ]:
        offending_ips = (
            RequestLog.objects.filter(
                organization_id=organization_id,
                zone=zone,
                timestamp__gte=window_start,
            )
            .values("source_ip")
            .annotate(hit_count=Count("id"))
            .filter(hit_count__gte=threshold)
        )

        for row in offending_ips:
            ip = row["source_ip"]
            # Skip if we already have a PENDING suggestion for this IP+zone
            if ThreatSuggestion.objects.filter(
                organization_id=organization_id,
                ip_address=ip,
                trigger_zone=zone,
                status=ThreatSuggestion.Status.PENDING,
            ).exists():
                continue

            # Gather sample data
            recent_logs = RequestLog.objects.filter(
                organization_id=organization_id,
                source_ip=ip,
                zone=zone,
                timestamp__gte=window_start,
            ).order_by("-timestamp")[:10]

            sample_paths = [log.path for log in recent_logs]
            all_signals = []
            for log in recent_logs:
                all_signals.extend(log.threat_signals or [])
            top_signals = [sig for sig, _ in Counter(all_signals).most_common(5)]

            ThreatSuggestion.objects.create(
                organization_id=organization_id,
                ip_address=ip,
                trigger_zone=zone,
                request_count=row["hit_count"],
                window_start=window_start,
                window_end=now,
                sample_paths=sample_paths,
                top_threat_signals=top_signals,
            )
            created += 1

    return created


# ── Analytics helpers ───────────────────────────────────────────────


def zone_distribution(organization_id, hours=24):
    """Return zone counts for the given time window."""
    since = timezone.now() - timedelta(hours=hours)
    return dict(
        RequestLog.objects.filter(
            organization_id=organization_id,
            timestamp__gte=since,
        )
        .values_list("zone")
        .annotate(count=Count("id"))
    )


def top_offending_ips(organization_id, hours=24, limit=10):
    """Return IPs with the most RED+GRAY requests."""
    since = timezone.now() - timedelta(hours=hours)
    return list(
        RequestLog.objects.filter(
            organization_id=organization_id,
            zone__in=[RequestLog.Zone.RED, RequestLog.Zone.GRAY],
            timestamp__gte=since,
        )
        .values("source_ip")
        .annotate(
            red_count=Count("id", filter=models_Q(zone=RequestLog.Zone.RED)),
            gray_count=Count("id", filter=models_Q(zone=RequestLog.Zone.GRAY)),
            total=Count("id"),
        )
        .order_by("-total")[:limit]
    )


def models_Q(**kwargs):
    """Helper to avoid import at module level (circular-safe)."""
    from django.db.models import Q

    return Q(**kwargs)


def zone_trend(organization_id, hours=24, bucket_minutes=60):
    """Return zone counts bucketed by time for charting."""
    from django.db.models.functions import TruncHour

    since = timezone.now() - timedelta(hours=hours)
    return list(
        RequestLog.objects.filter(
            organization_id=organization_id,
            timestamp__gte=since,
        )
        .annotate(bucket=TruncHour("timestamp"))
        .values("bucket", "zone")
        .annotate(count=Count("id"))
        .order_by("bucket")
    )
