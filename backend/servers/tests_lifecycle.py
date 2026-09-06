from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.models import Organization
from alert.models import Alert
from incident.models import Incident
from servers.models import MonitoringConnection, Servers, Service
from servers.services.lifecycle import (
    evaluate_all_services,
    evaluate_service,
    record_explicit_health,
)


@override_settings(SERVICE_STALE_AFTER_SECONDS=90, SERVICE_OFFLINE_AFTER_SECONDS=300)
class ServiceLifecycleTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.organization = Organization.objects.create(name="Acme", summary="Acme")
        self.server = Servers.objects.create(
            organization=self.organization,
            name="host",
            host_name="host-1",
            environment="prod",
            status=Servers.Status.HEALTHY,
            last_seen_at=self.now,
        )
        self.connection = MonitoringConnection.objects.create(
            server=self.server,
            status=MonitoringConnection.Status.CONNECTED,
            ingestion_health=MonitoringConnection.IngestionHealth.HEALTHY,
            last_metric_at=self.now,
        )
        self.service = Service.objects.create(
            server_id=self.server,
            service_name="payments",
            display_name="Payments",
            status=Servers.Status.HEALTHY,
            last_reported_at=self.now,
        )

    def test_recent_service_telemetry_is_healthy(self):
        state, reason, changed = evaluate_service(self.service.service_id, now=self.now)
        self.assertEqual(state, Servers.Status.HEALTHY)
        self.assertEqual(reason, "telemetry_received")
        self.assertFalse(changed)

    def test_collector_outage_marks_stale_without_crash_alert(self):
        old = self.now - timedelta(minutes=10)
        Service.objects.filter(pk=self.service.pk).update(last_reported_at=old)
        MonitoringConnection.objects.filter(pk=self.connection.pk).update(last_metric_at=old)

        state, reason, _ = evaluate_service(self.service.service_id, now=self.now)

        self.assertEqual(state, Servers.Status.STALE)
        self.assertEqual(reason, "collector_unavailable")
        self.assertFalse(Alert.objects.exists())
        self.assertFalse(Incident.objects.exists())

    def test_service_timeout_with_live_collector_opens_one_failure(self):
        Service.objects.filter(pk=self.service.pk).update(
            last_reported_at=self.now - timedelta(minutes=6)
        )

        first = evaluate_service(self.service.service_id, now=self.now)
        second = evaluate_service(self.service.service_id, now=self.now)

        self.assertEqual(first[0], Servers.Status.OFFLINE)
        self.assertEqual(first[1], "service_telemetry_timeout")
        self.assertFalse(second[2])
        self.assertEqual(Alert.objects.count(), 1)
        self.assertEqual(Incident.objects.count(), 1)
        self.assertEqual(Incident.objects.get().service, self.service)

    def test_recovery_resolves_failure(self):
        Service.objects.filter(pk=self.service.pk).update(
            last_reported_at=self.now - timedelta(minutes=6)
        )
        evaluate_service(self.service.service_id, now=self.now)
        recovered_at = self.now + timedelta(seconds=15)
        Service.objects.filter(pk=self.service.pk).update(last_reported_at=recovered_at)

        state, reason, changed = evaluate_service(
            self.service.service_id,
            now=recovered_at,
        )

        self.assertEqual(state, Servers.Status.HEALTHY)
        self.assertEqual(reason, "telemetry_received")
        self.assertTrue(changed)
        self.assertEqual(Alert.objects.get().state, Alert.State.RESOLVED)
        self.assertEqual(Incident.objects.get().status, Incident.Status.RESOLVED)

    def test_bulk_evaluator_reports_counts(self):
        result = evaluate_all_services(now=self.now)
        self.assertEqual(result, {"evaluated": 1, "changed": 0, "offline": 0})

    def test_two_explicit_failures_mark_offline_and_success_recovers(self):
        first = record_explicit_health(self.service.service_id, False, now=self.now)
        second = record_explicit_health(
            self.service.service_id,
            False,
            now=self.now + timedelta(seconds=15),
        )
        recovered = record_explicit_health(
            self.service.service_id,
            True,
            now=self.now + timedelta(seconds=30),
        )

        self.assertEqual(first[0], Servers.Status.WARNING)
        self.assertEqual(second[0], Servers.Status.OFFLINE)
        self.assertEqual(recovered[0], Servers.Status.HEALTHY)
        self.service.refresh_from_db()
        self.assertEqual(self.service.consecutive_failure_observations, 0)
        self.assertEqual(Alert.objects.get().state, Alert.State.RESOLVED)
