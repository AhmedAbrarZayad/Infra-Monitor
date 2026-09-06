from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Organization, OrganizationMembership, Users
from accounts.services.organization_service import OrganizationService
from alert.models import Alert
from incident.models import Incident, IncidentAlert, IncidentUpdate
from log.models import LogEntry
from ml_model.models import AnomalyAssignmentEvent, AnomalyDetection
from servers.models import (
    Servers,
    Service,
    ServiceAdminAssignment,
    ServiceAdminAssignmentEvent,
)


class OperationalAuthorizationMatrixTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Scoped", summary="Scoped")
        self.other_org = Organization.objects.create(name="Other", summary="Other")
        self.owner = self.user("owner")
        self.admin = self.user("assigned-admin")
        self.unassigned_admin = self.user("unassigned-admin")
        self.engineer = self.user("assigned-engineer")
        self.unassigned_engineer = self.user("unassigned-engineer")
        self.pending = self.user("pending")
        self.removed = self.user("removed")
        self.cross = self.user("cross")

        self.owner_membership = self.member(self.owner, "OWNER")
        self.admin_membership = self.member(self.admin, "ADMIN")
        self.unassigned_admin_membership = self.member(self.unassigned_admin, "ADMIN")
        self.engineer_membership = self.member(self.engineer, "ENGINEER")
        self.member(self.unassigned_engineer, "ENGINEER")
        OrganizationMembership.objects.create(
            organization=self.org,
            user=self.pending,
            role="ENGINEER",
            approved=False,
        )
        removed_membership = self.member(self.removed, "ENGINEER")
        removed_membership.delete()
        OrganizationMembership.objects.create(
            organization=self.other_org,
            user=self.cross,
            role="OWNER",
            approved=True,
        )

        self.server = Servers.objects.create(
            organization=self.org, name="host", host_name="host", environment="prod"
        )
        self.service = Service.objects.create(
            server_id=self.server, service_name="api", display_name="API"
        )
        self.sibling = Service.objects.create(
            server_id=self.server, service_name="worker", display_name="Worker"
        )
        ServiceAdminAssignment.objects.create(
            service=self.service,
            membership=self.admin_membership,
            assigned_by=self.owner,
        )

        self.incident = self.make_incident(
            "INC-SCOPED", self.service, assigned_to=self.engineer
        )
        self.sibling_incident = self.make_incident("INC-SIBLING", self.sibling)
        self.host_incident = self.make_incident("INC-HOST", None)
        self.anomaly = self.make_anomaly(self.service, assigned_to=self.engineer)
        self.sibling_anomaly = self.make_anomaly(self.sibling, minute=1)
        self.host_anomaly = self.make_anomaly(None, minute=2)
        self.alert = self.make_alert("scoped", self.service, self.anomaly)
        self.sibling_alert = self.make_alert("sibling", self.sibling, self.sibling_anomaly)
        self.host_alert = self.make_alert("host", None, self.host_anomaly)
        IncidentAlert.objects.create(incident_id=self.incident, alert_id=self.alert)
        self.log = self.make_log("scoped", self.service)
        self.sibling_log = self.make_log("sibling", self.sibling)
        self.host_log = self.make_log("host", None)
        self.base = f"/api/organizations/{self.org.pk}"

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
            organization=self.org, user=user, role=role, approved=True
        )

    def make_incident(self, code, service, assigned_to=None):
        return Incident.objects.create(
            organization=self.org,
            incident_code=code,
            server_id=self.server,
            service=service,
            assigned_to=assigned_to,
            title=code,
            description=code,
            category="TEST",
            severity="HIGH",
        )

    def make_anomaly(self, service, assigned_to=None, minute=0):
        end = timezone.now() + timedelta(minutes=minute)
        return AnomalyDetection.objects.create(
            organization=self.org,
            server_id=self.server,
            service_id=service,
            assigned_to=assigned_to,
            anomaly_score=-0.2,
            confidence_score=0.8,
            is_anomaly=True,
            feature_values={},
            window_started_at=end - timedelta(minutes=5),
            window_ended_at=end,
        )

    def make_alert(self, fingerprint, service, detection):
        return Alert.objects.create(
            organization=self.org,
            server_id=self.server,
            service_id=service,
            detection_id=detection,
            title=fingerprint,
            description=fingerprint,
            category="TEST",
            severity="HIGH",
            fingerprint=fingerprint,
        )

    def make_log(self, message, service):
        return LogEntry.objects.create(
            organization=self.org,
            server_id=self.server,
            service_id=service,
            source="test",
            log_level="INFO",
            message=message,
            logged_at=timezone.now(),
        )

    def authenticate(self, user):
        self.client.force_authenticate(user)

    def ids(self, path):
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        return {str(item["id"]) for item in response.data["results"]}

    def test_assigned_admin_sees_only_assigned_service_and_safe_parent_context(self):
        self.authenticate(self.admin)
        servers = self.client.get(f"{self.base}/servers/")
        self.assertEqual(servers.status_code, 200)
        parent = servers.data["results"][0]
        self.assertEqual(parent["service_count"], 1)
        self.assertEqual(parent["alert_count"], 1)
        self.assertEqual(parent["metrics"], {})
        self.assertEqual(parent["cpu_history"], [])
        self.assertEqual(
            self.ids(f"{self.base}/servers/{self.server.pk}/services/"),
            {str(self.service.pk)},
        )
        self.assertEqual(
            self.client.get(f"{self.base}/services/{self.sibling.pk}/").status_code, 404
        )
        self.assertEqual(
            self.ids(f"{self.base}/incidents/"), {str(self.incident.pk)}
        )
        incident_detail = self.client.get(f"{self.base}/incidents/{self.incident.pk}/")
        self.assertEqual(str(incident_detail.data["service_id"]), str(self.service.pk))
        self.assertEqual(incident_detail.data["service"], "API")
        self.assertEqual(self.ids(f"{self.base}/anomalies/"), {str(self.anomaly.pk)})
        self.assertEqual(self.ids(f"{self.base}/alerts/"), {str(self.alert.pk)})
        self.assertEqual(self.ids(f"{self.base}/logs/"), {str(self.log.pk)})

    def test_engineer_sees_only_assigned_work_and_related_context(self):
        self.authenticate(self.engineer)
        self.assertEqual(self.ids(f"{self.base}/incidents/"), {str(self.incident.pk)})
        self.assertEqual(self.ids(f"{self.base}/anomalies/"), {str(self.anomaly.pk)})
        self.assertEqual(self.ids(f"{self.base}/alerts/"), {str(self.alert.pk)})
        self.assertEqual(self.ids(f"{self.base}/logs/"), {str(self.log.pk)})
        parent = self.client.get(f"{self.base}/servers/{self.server.pk}/")
        self.assertEqual(parent.status_code, 200)
        self.assertEqual(parent.data["service_count"], 1)
        self.assertEqual(parent.data["metrics"], {})
        self.assertEqual(
            self.client.get(f"{self.base}/servers/{self.server.pk}/metrics/").status_code,
            403,
        )
        self.assertEqual(
            self.client.get(f"{self.base}/services/{self.sibling.pk}/").status_code, 404
        )
        context = self.client.get(f"{self.base}/assistant/context/")
        self.assertEqual(
            {str(item["id"]) for item in context.data["anomalies"]},
            {str(self.anomaly.pk)},
        )

    def test_unassigned_pending_removed_and_cross_members_have_no_access(self):
        for user, expected in [
            (self.unassigned_admin, 200),
            (self.unassigned_engineer, 200),
            (self.pending, 404),
            (self.removed, 404),
            (self.cross, 404),
        ]:
            with self.subTest(user=user.username):
                self.authenticate(user)
                response = self.client.get(f"{self.base}/servers/")
                self.assertEqual(response.status_code, expected)
                if expected == 200:
                    self.assertEqual(response.data["results"], [])

    def test_engineer_actions_and_membership_listing_are_forbidden(self):
        self.authenticate(self.engineer)
        self.assertEqual(
            self.client.post(f"{self.base}/alerts/{self.alert.pk}/acknowledge/").status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                f"{self.base}/incidents/{self.incident.pk}/assign-to-me/"
            ).status_code,
            404,
        )
        self.assertEqual(self.client.get(f"{self.base}/members/").status_code, 403)
        self.assertEqual(
            self.client.post(
                f"{self.base}/incidents/{self.incident.pk}/assignment/",
                {"user_id": self.engineer.pk},
            ).status_code,
            403,
        )

    def test_owner_assigns_admin_and_admin_assigns_only_in_scope_work(self):
        self.authenticate(self.owner)
        response = self.client.put(
            f"{self.base}/services/{self.sibling.pk}/admins/",
            {"membership_ids": [str(self.unassigned_admin_membership.pk)]},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.authenticate(self.unassigned_admin)
        self.assertEqual(
            self.client.get(f"{self.base}/services/{self.sibling.pk}/").status_code, 200
        )
        self.assertEqual(
            self.client.get(f"{self.base}/services/{self.service.pk}/").status_code, 404
        )
        assigned = self.client.post(
            f"{self.base}/incidents/{self.sibling_incident.pk}/assignment/",
            {"user_id": self.unassigned_engineer.pk},
            format="json",
        )
        self.assertEqual(assigned.status_code, 200)
        self.assertEqual(assigned.data["assigned_to"]["id"], self.unassigned_engineer.pk)
        anomaly_assigned = self.client.post(
            f"{self.base}/anomalies/{self.sibling_anomaly.pk}/assignment/",
            {"user_id": self.unassigned_engineer.pk},
            format="json",
        )
        self.assertEqual(anomaly_assigned.status_code, 200)
        self.assertEqual(
            anomaly_assigned.data["assigned_to"]["id"], self.unassigned_engineer.pk
        )
        self.assertEqual(anomaly_assigned.data["assigned_by"]["id"], self.unassigned_admin.pk)
        invalid_assignee = self.client.post(
            f"{self.base}/incidents/{self.sibling_incident.pk}/assignment/",
            {"user_id": self.admin.pk},
            format="json",
        )
        self.assertEqual(invalid_assignee.status_code, 404)
        self.assertEqual(
            self.client.post(
                f"{self.base}/incidents/{self.incident.pk}/assignment/",
                {"user_id": self.unassigned_engineer.pk},
                format="json",
            ).status_code,
            404,
        )

    def test_evidence_and_bulk_actions_do_not_touch_hidden_siblings(self):
        self.authenticate(self.engineer)
        evidence = self.client.get(f"{self.base}/incidents/{self.incident.pk}/evidence/")
        self.assertEqual(evidence.status_code, 200)
        self.assertEqual({item["message"] for item in evidence.data["logs"]}, {"scoped"})
        self.assertNotIn(str(self.sibling_anomaly.pk), {str(item["id"]) for item in evidence.data["anomalies"]})
        response = self.client.post(
            f"{self.base}/incidents/bulk-acknowledge/",
            {"incident_ids": [str(self.incident.pk), str(self.sibling_incident.pk)]},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.sibling_incident.refresh_from_db()
        self.assertEqual(self.sibling_incident.status, "NEW")

    def test_admin_demotion_immediately_removes_service_access(self):
        OrganizationService.change_role(
            organization=self.org,
            target_user_id=self.admin.pk,
            role="ENGINEER",
            actor=self.owner,
        )
        self.assertFalse(
            ServiceAdminAssignment.objects.filter(membership=self.admin_membership).exists()
        )
        event = ServiceAdminAssignmentEvent.objects.get(service=self.service)
        self.assertEqual(event.action, "UNASSIGNED")
        self.assertEqual(event.actor_id, self.owner.pk)
        self.assertEqual(event.previous_subject_id, self.admin.pk)
        self.authenticate(self.admin)
        self.assertEqual(self.client.get(f"{self.base}/services/{self.service.pk}/").status_code, 404)

    def test_admin_removal_records_service_unassignment(self):
        self.authenticate(self.owner)
        response = self.client.delete(f"{self.base}/members/{self.admin.pk}/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(
            ServiceAdminAssignment.objects.filter(service=self.service).exists()
        )
        event = ServiceAdminAssignmentEvent.objects.get(service=self.service)
        self.assertEqual(event.action, "UNASSIGNED")
        self.assertEqual(event.actor_id, self.owner.pk)
        self.assertEqual(event.previous_subject_id, self.admin.pk)

    def test_service_admin_replacement_is_audited_and_noop_is_not(self):
        self.authenticate(self.owner)
        path = f"{self.base}/services/{self.sibling.pk}/admins/"
        history_path = f"{path}history/"
        payload = {"membership_ids": [str(self.unassigned_admin_membership.pk)]}

        added = self.client.put(path, payload, format="json")
        self.assertEqual(added.status_code, 200)
        self.assertEqual(ServiceAdminAssignmentEvent.objects.count(), 1)
        event = self.client.get(history_path).data["results"][0]
        self.assertEqual(event["resource_type"], "SERVICE")
        self.assertEqual(event["action"], "ASSIGNED")
        self.assertEqual(event["actor"]["id"], self.owner.pk)
        self.assertEqual(event["new_subject"]["id"], self.unassigned_admin.pk)

        noop = self.client.put(path, payload, format="json")
        self.assertEqual(noop.status_code, 200)
        self.assertEqual(ServiceAdminAssignmentEvent.objects.count(), 1)

        removed = self.client.put(path, {"membership_ids": []}, format="json")
        self.assertEqual(removed.status_code, 200)
        self.assertEqual(ServiceAdminAssignmentEvent.objects.count(), 2)
        latest = self.client.get(history_path).data["results"][0]
        self.assertEqual(latest["action"], "UNASSIGNED")
        self.assertEqual(latest["previous_subject"]["id"], self.unassigned_admin.pk)

        self.authenticate(self.admin)
        self.assertEqual(self.client.get(history_path).status_code, 403)

    def test_incident_patch_assignment_history_noop_and_stale_precondition(self):
        self.authenticate(self.admin)
        path = f"{self.base}/incidents/{self.incident.pk}/assignment/"

        reassigned = self.client.patch(
            path,
            {
                "user_id": self.unassigned_engineer.pk,
                "expected_user_id": self.engineer.pk,
            },
            format="json",
        )
        self.assertEqual(reassigned.status_code, 200)
        self.assertEqual(reassigned.data["assigned_to"]["id"], self.unassigned_engineer.pk)
        self.assertEqual(
            IncidentUpdate.objects.filter(action="REASSIGNED").count(), 1
        )

        noop = self.client.patch(
            path,
            {
                "user_id": self.unassigned_engineer.pk,
                "expected_user_id": self.unassigned_engineer.pk,
            },
            format="json",
        )
        self.assertEqual(noop.status_code, 200)
        self.assertEqual(
            IncidentUpdate.objects.filter(action="REASSIGNED").count(), 1
        )

        stale = self.client.patch(
            path,
            {"user_id": None, "expected_user_id": self.engineer.pk},
            format="json",
        )
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.data["code"], "assignment_changed")
        self.assertEqual(stale.data["assigned_to"]["id"], self.unassigned_engineer.pk)

        cleared = self.client.patch(
            path,
            {"user_id": None, "expected_user_id": self.unassigned_engineer.pk},
            format="json",
        )
        self.assertEqual(cleared.status_code, 200)
        self.assertIsNone(cleared.data["assigned_to"])
        history = self.client.get(
            f"{self.base}/incidents/{self.incident.pk}/assignment-history/"
        )
        self.assertEqual(history.status_code, 200)
        self.assertEqual(
            [item["action"] for item in history.data["results"]],
            ["UNASSIGNED", "REASSIGNED"],
        )
        self.assertEqual(
            history.data["results"][1]["previous_subject"]["id"], self.engineer.pk
        )

    def test_anomaly_patch_assignment_history_and_engineer_read_only_access(self):
        self.authenticate(self.admin)
        path = f"{self.base}/anomalies/{self.anomaly.pk}/assignment/"
        response = self.client.patch(
            path,
            {
                "user_id": self.unassigned_engineer.pk,
                "expected_user_id": self.engineer.pk,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(AnomalyAssignmentEvent.objects.count(), 1)

        noop = self.client.patch(
            path,
            {
                "user_id": self.unassigned_engineer.pk,
                "expected_user_id": self.unassigned_engineer.pk,
            },
            format="json",
        )
        self.assertEqual(noop.status_code, 200)
        self.assertEqual(AnomalyAssignmentEvent.objects.count(), 1)

        stale = self.client.patch(
            path,
            {"user_id": None, "expected_user_id": self.engineer.pk},
            format="json",
        )
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(AnomalyAssignmentEvent.objects.count(), 1)

        history_path = f"{self.base}/anomalies/{self.anomaly.pk}/assignment-history/"
        self.authenticate(self.unassigned_engineer)
        history = self.client.get(history_path)
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.data["results"][0]["action"], "REASSIGNED")
        self.assertEqual(
            self.client.patch(
                path,
                {"user_id": self.engineer.pk, "expected_user_id": self.unassigned_engineer.pk},
                format="json",
            ).status_code,
            403,
        )

        self.authenticate(self.engineer)
        self.assertEqual(self.client.get(history_path).status_code, 404)

    def test_assignment_targets_must_be_approved_engineers_in_organization(self):
        self.authenticate(self.admin)
        for target in [self.admin, self.pending, self.cross]:
            with self.subTest(target=target.username):
                response = self.client.patch(
                    f"{self.base}/incidents/{self.incident.pk}/assignment/",
                    {"user_id": target.pk, "expected_user_id": self.engineer.pk},
                    format="json",
                )
                self.assertEqual(response.status_code, 404)
        self.incident.refresh_from_db()
        self.assertEqual(self.incident.assigned_to_id, self.engineer.pk)
