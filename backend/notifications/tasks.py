import logging

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from accounts.models import OrganizationMembership
from common.authorization import anomalies_visible_to, incidents_visible_to

from .models import DeviceRegistration, SentNotification

logger = logging.getLogger(__name__)


def _firebase_app():
    import firebase_admin

    try:
        return firebase_admin.get_app()
    except ValueError:
        options = {"httpTimeout": settings.FCM_HTTP_TIMEOUT_SECONDS}
        if settings.FIREBASE_PROJECT_ID:
            options["projectId"] = settings.FIREBASE_PROJECT_ID
        return firebase_admin.initialize_app(options=options)


def _still_authorized(notification):
    membership = OrganizationMembership.objects.filter(
        organization=notification.organization,
        user=notification.user,
        approved=True,
    ).first()
    if not membership:
        return False
    if notification.resource_type == "INCIDENT":
        return incidents_visible_to(membership).filter(pk=notification.resource_id).exists()
    if notification.resource_type == "ANOMALY":
        return anomalies_visible_to(membership).filter(pk=notification.resource_id).exists()
    return False


@shared_task(
    bind=True,
    name="notifications.deliver",
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def deliver_notification(self, notification_id):
    notification = SentNotification.objects.select_related("user", "organization").get(
        pk=notification_id
    )
    if notification.state == SentNotification.State.SENT:
        return {"state": notification.state}
    if not _still_authorized(notification):
        notification.state = SentNotification.State.SKIPPED
        notification.provider_error = "authorization_revoked"
        notification.save(update_fields=["state", "provider_error"])
        return {"state": notification.state}

    devices = list(DeviceRegistration.objects.filter(user=notification.user, active=True))
    if not settings.FCM_ENABLED or not devices:
        notification.state = SentNotification.State.SKIPPED
        notification.provider_error = "fcm_disabled" if not settings.FCM_ENABLED else "no_device"
        notification.save(update_fields=["state", "provider_error"])
        return {"state": notification.state}

    from firebase_admin import exceptions, messaging

    sent_ids = []
    for device in devices:
        try:
            message_id = messaging.send(
                messaging.Message(
                    token=device.token,
                    notification=messaging.Notification(
                        title=notification.title, body=notification.body
                    ),
                    data={
                        "event_type": notification.event_type,
                        "organization_id": str(notification.organization_id),
                        "resource_type": notification.resource_type,
                        "resource_id": str(notification.resource_id),
                    },
                    android=messaging.AndroidConfig(priority="high"),
                ),
                app=_firebase_app(),
            )
            sent_ids.append(message_id)
        except messaging.UnregisteredError:
            device.active = False
            device.save(update_fields=["active"])
        except (exceptions.ResourceExhaustedError, exceptions.UnavailableError, exceptions.DeadlineExceededError) as exc:
            raise ConnectionError(type(exc).__name__) from exc
        except (messaging.SenderIdMismatchError, messaging.ThirdPartyAuthError) as exc:
            logger.warning("Permanent FCM configuration error: %s", type(exc).__name__)

    notification.state = SentNotification.State.SENT if sent_ids else SentNotification.State.FAILED
    notification.provider_message_id = ",".join(sent_ids)[:255]
    notification.provider_error = "" if sent_ids else "no_successful_delivery"
    notification.sent_at = timezone.now() if sent_ids else None
    notification.save(update_fields=["state", "provider_message_id", "provider_error", "sent_at"])
    return {"state": notification.state, "sent": len(sent_ids)}
