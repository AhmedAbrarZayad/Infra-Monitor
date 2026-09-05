from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Organization, OrganizationMembership, Users
from ai.models import AssistantConversation, AssistantMessage, AssistantWebSocketTicket
from ai.services import consume_websocket_ticket, issue_websocket_ticket, stream_gemini_response
from infra_monitor.asgi import application
from incident.models import Incident
from ml_model.models import AnomalyDetection
from ml_model.services import FEATURE_NAMES
from servers.models import Servers, Service


@override_settings(
    GEMINI_API_KEY="test-key",
    GEMINI_MODEL="test-gemini",
    ASSISTANT_WS_TICKET_TTL_SECONDS=60,
)
class AssistantTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.organization = Organization.objects.create(name="School Lab", summary="Lab")
        self.user = Users.objects.create_user(
            username="member", email="member@example.com", password="pass", is_email_verified=True
        )
        OrganizationMembership.objects.create(
            organization=self.organization, user=self.user, role="ENGINEER", approved=True
        )
        self.server = Servers.objects.create(
            organization=self.organization,
            name="Ubuntu Lab",
            host_name="ubuntu-lab",
            environment="test",
        )
        self.service = Service.objects.create(
            server_id=self.server,
            service_name="demo",
            display_name="demo-load",
            status=Servers.Status.HEALTHY,
            lifecycle_reason="telemetry_current",
        )
        end = timezone.now()
        self.anomaly = AnomalyDetection.objects.create(
            organization=self.organization,
            server_id=self.server,
            service_id=self.service,
            anomaly_score=-0.2,
            confidence_score=0.2,
            is_anomaly=True,
            feature_values={name: float(index + 1) for index, name in enumerate(FEATURE_NAMES)},
            model_version="model-1",
            window_started_at=end - timedelta(minutes=5),
            window_ended_at=end,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.base = f"/api/organizations/{self.organization.pk}/assistant"

    def test_context_and_conversation_are_anomaly_scoped_and_idempotent(self):
        context = self.client.get(f"{self.base}/context/")
        self.assertEqual(context.status_code, 200)
        self.assertEqual(context.data["selected_anomaly"]["id"], self.anomaly.pk)
        self.assertEqual(len(context.data["selected_anomaly"]["evidence"]), 6)
        self.assertEqual(context.data["selected_anomaly"]["lifecycle"]["status"], "HEALTHY")

        first = self.client.post(
            f"{self.base}/conversations/", {"anomaly_id": str(self.anomaly.pk)}, format="json"
        )
        second = self.client.post(
            f"{self.base}/conversations/", {"anomaly_id": str(self.anomaly.pk)}, format="json"
        )
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data["id"], second.data["id"])
        self.assertEqual(AssistantConversation.objects.count(), 1)

    def test_cross_organization_resources_are_hidden(self):
        outsider_org = Organization.objects.create(name="Other", summary="Other")
        outsider = Users.objects.create_user(
            username="outsider", email="outsider@example.com", password="pass"
        )
        OrganizationMembership.objects.create(
            organization=outsider_org, user=outsider, role="ENGINEER", approved=True
        )
        self.client.force_authenticate(outsider)
        response = self.client.get(
            f"/api/organizations/{outsider_org.pk}/assistant/context/",
            {"anomaly_id": str(self.anomaly.pk)},
        )
        self.assertEqual(response.status_code, 404)

    def test_ticket_is_hashed_bound_and_single_use(self):
        conversation = AssistantConversation.objects.create(
            organization=self.organization, user_id=self.user, anomaly=self.anomaly, title="Anomaly"
        )
        response = self.client.post(
            f"{self.base}/websocket-tickets/",
            {"conversation_id": str(conversation.pk)},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        raw = response.data["ticket"]
        ticket = AssistantWebSocketTicket.objects.get()
        self.assertNotEqual(ticket.token_hash, raw)
        self.assertEqual(
            consume_websocket_ticket(
                token=raw,
                organization_id=self.organization.pk,
                conversation_id=conversation.pk,
            ),
            self.user.pk,
        )
        self.assertIsNone(
            consume_websocket_ticket(
                token=raw,
                organization_id=self.organization.pk,
                conversation_id=conversation.pk,
            )
        )
        expired_token, expired = issue_websocket_ticket(
            organization=self.organization, user=self.user, conversation=conversation
        )
        expired.expires_at = timezone.now() - timedelta(seconds=1)
        expired.save(update_fields=["expires_at"])
        self.assertIsNone(
            consume_websocket_ticket(
                token=expired_token,
                organization_id=self.organization.pk,
                conversation_id=conversation.pk,
            )
        )

    def test_stream_persists_messages_without_changing_lifecycle(self):
        conversation = AssistantConversation.objects.create(
            organization=self.organization, user_id=self.user, anomaly=self.anomaly, title="Anomaly"
        )
        token, _ = issue_websocket_ticket(
            organization=self.organization, user=self.user, conversation=conversation
        )

        async def fake_stream(contents):
            self.assertIn("crash_not_confirmed", str(contents))
            yield "Check CPU and memory first."

        async def scenario():
            path = (
                f"/ws/organizations/{self.organization.pk}/assistant/conversations/"
                f"{conversation.pk}/?ticket={token}"
            )
            communicator = WebsocketCommunicator(application, path)
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            await communicator.send_json_to(
                {
                    "type": "user_message",
                    "client_message_id": "7781fb4d-b81d-4a20-b153-c030ff57983e",
                    "text": "What should I check?",
                }
            )
            event_types = []
            while "generation_completed" not in event_types:
                event = await communicator.receive_json_from(timeout=2)
                event_types.append(event["type"])
            await communicator.disconnect()
            self.assertEqual(event_types[0:2], ["message_ack", "generation_started"])
            self.assertIn("token_delta", event_types)

        with patch("ai.consumers.stream_gemini_response", fake_stream):
            async_to_sync(scenario)()

        self.assertEqual(AssistantMessage.objects.count(), 2)
        self.assertEqual(Incident.objects.count(), 0)
        self.service.refresh_from_db()
        self.assertEqual(self.service.status, Servers.Status.HEALTHY)

    def test_google_sdk_stream_coroutine_is_awaited_then_iterated(self):
        class FakeModels:
            async def generate_content_stream(self, **kwargs):
                async def chunks():
                    yield SimpleNamespace(text="first ")
                    yield SimpleNamespace(text="second")

                return chunks()

        class FakeAio:
            models = FakeModels()

            async def aclose(self):
                return None

        fake_client = SimpleNamespace(aio=FakeAio())

        async def collect():
            return [chunk async for chunk in stream_gemini_response([{"role": "user"}])]

        with patch("google.genai.Client", return_value=fake_client):
            self.assertEqual(async_to_sync(collect)(), ["first ", "second"])
