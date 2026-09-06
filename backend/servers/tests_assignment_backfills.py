from datetime import timedelta
from importlib import import_module

from django.apps import apps
from django.test import TestCase
from django.utils import timezone

from accounts.models import Organization, OrganizationMembership, Users
from incident.models import Incident, IncidentUpdate
from ml_model.models import AnomalyAssignmentEvent, AnomalyDetection
from servers.models import (
    Servers,
    Service,
    ServiceAdminAssignment,
    ServiceAdminAssignmentEvent,
)


class AssignmentBackfillTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Legacy", summary="Legacy")
        self.owner = self.user("owner")
        self.admin = self.user("admin")
        self.engineer = self.user("engineer")
        self.owner_membership = self.member(self.owner, "OWNER")
        self.admin_membership = self.member(self.admin, "ADMIN")
        self.member(self.engineer, "ENGINEER")
        self.server = Servers.objects.create(
            organization=self.organization,
            name="legacy-host",
            host_name="legacy-host",
            environment="prod",
        )
        self.service = Service.objects.create(
            server_id=self.server,
            service_name="api",
            display_name="API",
        )

    @staticmethod
    def user(name):
        return Users.objects.create_user(
            username=name,
            email=f"{name}@example.com",
            password="password123",
            is_email_verified=True,
        )

    def member(self, user, role):
        return OrganizationMembership.objects.create(
            organization=self.organization,
            user=user,
            role=role,
            approved=True,
        )

    def test_service_assignment_backfill_preserves_actor_subject_and_time(self):
        assignment = ServiceAdminAssignment.objects.create(
            service=self.service,
            membership=self.admin_membership,
            assigned_by=self.owner,
        )
        migration = import_module("servers.migrations.0008_serviceadminassignmentevent")
        migration.backfill_service_admin_events(apps, None)

        event = ServiceAdminAssignmentEvent.objects.get(service=self.service)
        self.assertEqual(event.actor_id, self.owner.pk)
        self.assertEqual(event.new_subject_id, self.admin.pk)
        self.assertEqual(event.created_at, assignment.created_at)

    def test_incident_legacy_numeric_assignment_comment_is_recovered(self):
        incident = Incident.objects.create(
            organization=self.organization,
            incident_code="LEGACY-1",
            server_id=self.server,
            service=self.service,
            title="Legacy",
            description="Legacy",
            category="TEST",
            severity="HIGH",
        )
        update = IncidentUpdate.objects.create(
            incident_id=incident,
            user_id=self.owner,
            action="ASSIGNED",
            comment=str(self.engineer.pk),
        )
        migration = import_module("incident.migrations.0007_incidentupdate_assignment_subjects")
        migration.backfill_incident_assignment_subjects(apps, None)

        update.refresh_from_db()
        self.assertEqual(update.new_subject_id, self.engineer.pk)

    def test_anomaly_assignment_backfill_uses_original_assignment_metadata(self):
        assigned_at = timezone.now() - timedelta(days=1)
        anomaly = AnomalyDetection.objects.create(
            organization=self.organization,
            server_id=self.server,
            service_id=self.service,
            assigned_to=self.engineer,
            assigned_by=self.owner,
            assigned_at=assigned_at,
            anomaly_score=-0.2,
            confidence_score=0.8,
            is_anomaly=True,
            feature_values={},
            window_started_at=timezone.now() - timedelta(minutes=5),
            window_ended_at=timezone.now(),
        )
        migration = import_module("ml_model.migrations.0007_anomalyassignmentevent")
        migration.backfill_anomaly_assignment_events(apps, None)

        event = AnomalyAssignmentEvent.objects.get(anomaly=anomaly)
        self.assertEqual(event.actor_id, self.owner.pk)
        self.assertEqual(event.new_subject_id, self.engineer.pk)
        self.assertEqual(event.created_at, assigned_at)
