"""Celery tasks for the Request Shield feature.

These run periodically via Celery Beat to classify pending request logs,
escalate gray-zone entries to Gemini, and generate threat suggestions.
"""

import asyncio
import logging

from celery import shared_task

from accounts.models import Organization

logger = logging.getLogger(__name__)


@shared_task(name="sanitize.classify_request_batch")
def classify_request_batch():
    """Classify pending request logs for all organizations."""
    from sanitize.services import classify_pending_batch

    batch_size = _setting("REQUEST_SHIELD_CLASSIFY_BATCH_SIZE", 100)
    total = 0
    for org in Organization.objects.all():
        classified = classify_pending_batch(org.id, batch_size=batch_size)
        if classified:
            logger.info("Classified %d request logs for org=%s", classified, org.id)
            total += classified
    return total


@shared_task(name="sanitize.escalate_gray_requests")
def escalate_gray_requests():
    """Escalate GRAY-zone requests to Gemini for deeper analysis."""
    from sanitize.services import escalate_gray_to_gemini

    total = 0
    for org in Organization.objects.all():
        escalated = asyncio.run(escalate_gray_to_gemini(org.id))
        if escalated:
            logger.info("Gemini escalated %d gray requests for org=%s", escalated, org.id)
            total += escalated
    return total


@shared_task(name="sanitize.generate_threat_suggestions")
def generate_threat_suggestions():
    """Generate threat suggestions for IPs exceeding zone thresholds."""
    from sanitize.services import generate_threat_suggestions as _generate

    total = 0
    for org in Organization.objects.all():
        created = _generate(org.id)
        if created:
            logger.info("Created %d threat suggestions for org=%s", created, org.id)
            total += created
    return total


def _setting(name, default):
    from django.conf import settings

    return getattr(settings, name, default)
