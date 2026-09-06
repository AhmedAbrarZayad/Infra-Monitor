"""Central operational visibility and capability rules.

All helpers expect an approved membership returned by
``get_organization_membership``. Collection and detail views must both use
these querysets so hidden objects consistently return 404.
"""

from django.db.models import Q

from accounts.models import OrganizationMembership


OWNER = OrganizationMembership.RoleEnum.OWNER
ADMIN = OrganizationMembership.RoleEnum.ADMIN
ENGINEER = OrganizationMembership.RoleEnum.ENGINEER


def services_visible_to(membership, queryset=None):
    from servers.models import Service

    queryset = queryset if queryset is not None else Service.objects.all()
    queryset = queryset.filter(server_id__organization=membership.organization)
    if membership.role == OWNER:
        return queryset
    if membership.role == ADMIN:
        return queryset.filter(admin_assignments__membership=membership).distinct()
    return queryset.filter(
        Q(incidents__assigned_to=membership.user)
        | Q(anomaly_detections__assigned_to=membership.user)
    ).distinct()


def servers_visible_to(membership, queryset=None):
    from servers.models import Servers

    queryset = queryset if queryset is not None else Servers.objects.all()
    queryset = queryset.filter(organization=membership.organization)
    if membership.role == OWNER:
        return queryset
    service_server_ids = services_visible_to(membership).values("server_id_id")
    return queryset.filter(server_id__in=service_server_ids).distinct()


def incidents_visible_to(membership, queryset=None):
    from incident.models import Incident

    queryset = queryset if queryset is not None else Incident.objects.all()
    queryset = queryset.filter(organization=membership.organization)
    if membership.role == OWNER:
        return queryset
    if membership.role == ADMIN:
        return queryset.filter(
            service__isnull=False,
            service__admin_assignments__membership=membership,
        ).distinct()
    return queryset.filter(
        service__isnull=False,
        assigned_to=membership.user,
    ).distinct()


def anomalies_visible_to(membership, queryset=None):
    from ml_model.models import AnomalyDetection

    queryset = queryset if queryset is not None else AnomalyDetection.objects.all()
    queryset = queryset.filter(organization=membership.organization)
    if membership.role == OWNER:
        return queryset
    if membership.role == ADMIN:
        return queryset.filter(
            service_id__isnull=False,
            service_id__admin_assignments__membership=membership,
        ).distinct()
    return queryset.filter(
        service_id__isnull=False,
        assigned_to=membership.user,
    ).distinct()


def alerts_visible_to(membership, queryset=None):
    from alert.models import Alert

    queryset = queryset if queryset is not None else Alert.objects.all()
    queryset = queryset.filter(organization=membership.organization)
    if membership.role == OWNER:
        return queryset
    if membership.role == ADMIN:
        return queryset.filter(
            service_id__isnull=False,
            service_id__admin_assignments__membership=membership,
        ).distinct()
    return queryset.filter(
        service_id__isnull=False,
    ).filter(
        Q(incidentalert__incident_id__assigned_to=membership.user)
        | Q(detection_id__assigned_to=membership.user)
    ).distinct()


def logs_visible_to(membership, queryset=None):
    from log.models import LogEntry

    queryset = queryset if queryset is not None else LogEntry.objects.all()
    queryset = queryset.filter(organization=membership.organization)
    if membership.role == OWNER:
        return queryset
    visible_ids = services_visible_to(membership).values("service_id")
    return queryset.filter(service_id__isnull=False, service_id__in=visible_ids).distinct()


def can_manage_service(membership, service):
    if membership.role == OWNER:
        return True
    return membership.role == ADMIN and service.admin_assignments.filter(
        membership=membership
    ).exists()


def can_manage_work(membership, work_item):
    """Whether a member can assign or administratively act on scoped work."""
    if membership.role == OWNER:
        return True
    service = getattr(work_item, "service", None) or getattr(work_item, "service_id", None)
    return bool(service and membership.role == ADMIN and can_manage_service(membership, service))


def can_operate_work(membership, work_item):
    return can_manage_work(membership, work_item) or (
        membership.role == ENGINEER
        and getattr(work_item, "assigned_to_id", None) == membership.user_id
    )


def approved_engineers(organization):
    return OrganizationMembership.objects.filter(
        organization=organization,
        approved=True,
        role=ENGINEER,
    ).select_related("user")
