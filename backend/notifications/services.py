from django.db import transaction

from accounts.models import OrganizationMembership, UserPreference

from .models import SentNotification


def _enabled_user_ids(user_ids):
    return set(
        UserPreference.objects.filter(
            user_id__in=user_ids, notifications_enabled=True
        ).values_list("user_id", flat=True)
    )


def _queue(*, organization, users, event_type, resource_type, resource_id, key, title, body):
    user_ids = _enabled_user_ids({user.pk for user in users})
    notification_ids = []
    for user_id in user_ids:
        notification, created = SentNotification.objects.get_or_create(
            user_id=user_id,
            deduplication_key=key,
            defaults={
                "organization": organization,
                "event_type": event_type,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "title": title,
                "body": body,
            },
        )
        if created:
            notification_ids.append(str(notification.pk))

    if notification_ids:
        from .tasks import deliver_notification

        transaction.on_commit(
            lambda: [deliver_notification.delay(item) for item in notification_ids]
        )


def notify_incident_created(incident):
    assignments = incident.service.admin_assignments.select_related("membership__user")
    users = [item.membership.user for item in assignments if item.membership.approved]
    if not users:
        users = [
            item.user
            for item in OrganizationMembership.objects.filter(
                organization=incident.organization,
                approved=True,
                role=OrganizationMembership.RoleEnum.OWNER,
            ).select_related("user")
        ]
    _queue(
        organization=incident.organization,
        users=users,
        event_type="INCIDENT_CREATED",
        resource_type="INCIDENT",
        resource_id=incident.pk,
        key=f"incident:{incident.pk}:created:{incident.detected_at.isoformat()}",
        title="Critical incident detected",
        body="Open Infra Monitor to review the affected service.",
    )


def notify_anomaly_created(anomaly):
    assignments = anomaly.service_id.admin_assignments.select_related("membership__user")
    users = [item.membership.user for item in assignments if item.membership.approved]
    if not users:
        users = [
            item.user
            for item in OrganizationMembership.objects.filter(
                organization=anomaly.organization,
                approved=True,
                role=OrganizationMembership.RoleEnum.OWNER,
            ).select_related("user")
        ]
    _queue(
        organization=anomaly.organization,
        users=users,
        event_type="ANOMALY_CREATED",
        resource_type="ANOMALY",
        resource_id=anomaly.pk,
        key=f"anomaly:{anomaly.pk}:created",
        title="Anomaly detected",
        body="Open Infra Monitor to review the detection.",
    )


def notify_assignment(work_item, resource_type, version):
    if not work_item.assigned_to_id:
        return
    _queue(
        organization=work_item.organization,
        users=[work_item.assigned_to],
        event_type=f"{resource_type}_ASSIGNED",
        resource_type=resource_type,
        resource_id=work_item.pk,
        key=f"{resource_type.lower()}:{work_item.pk}:assigned:{version}",
        title=f"{resource_type.title()} assigned to you",
        body="Open Infra Monitor to review the assigned work.",
    )
