import asyncio
import logging
import uuid
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.conf import settings

from ai.models import AssistantConversation, AssistantMessage
from ai.presenters import present_message
from ai.services import (
    anomaly_evidence_snapshot,
    consume_websocket_ticket,
    gemini_contents,
    stream_gemini_response,
)
from accounts.models import OrganizationMembership
from common.authorization import anomalies_visible_to


logger = logging.getLogger(__name__)


@database_sync_to_async
def authenticate_ticket(token, organization_id, conversation_id):
    return consume_websocket_ticket(
        token=token,
        organization_id=organization_id,
        conversation_id=conversation_id,
    )


@database_sync_to_async
def load_conversation(conversation_id, organization_id, user_id):
    membership = OrganizationMembership.objects.filter(
        organization_id=organization_id,
        user_id=user_id,
        approved=True,
    ).first()
    if membership is None:
        return None
    return (
        AssistantConversation.objects.select_related(
            "anomaly__service_id", "anomaly__server_id"
        )
        .filter(
            pk=conversation_id,
            organization_id=organization_id,
            user_id_id=user_id,
            anomaly__is_anomaly=True,
            anomaly__in=anomalies_visible_to(membership),
        )
        .first()
    )


@database_sync_to_async
def persist_user_message(conversation, client_message_id, text):
    return AssistantMessage.objects.get_or_create(
        conversation_id=conversation,
        client_message_id=client_message_id,
        defaults={"sender_type": AssistantMessage.Sender.USER, "message": text},
    )


@database_sync_to_async
def existing_assistant_response(conversation, client_message_id):
    return AssistantMessage.objects.filter(
        conversation_id=conversation,
        sender_type=AssistantMessage.Sender.ASSISTANT,
        response_to_client_message_id=client_message_id,
    ).first()


@database_sync_to_async
def recent_messages(conversation):
    latest = list(
        AssistantMessage.objects.filter(conversation_id=conversation)
        .order_by("-created_at", "-message_id")[:20]
    )
    return list(reversed(latest))


@database_sync_to_async
def persist_assistant_message(conversation, client_message_id, text, evidence):
    message, _ = AssistantMessage.objects.get_or_create(
        conversation_id=conversation,
        response_to_client_message_id=client_message_id,
        defaults={
            "sender_type": AssistantMessage.Sender.ASSISTANT,
            "message": text,
            "evidence": {
                "anomaly_id": evidence["anomaly_id"],
                "client_message_id": str(client_message_id),
                "model": settings.GEMINI_MODEL,
                "citations": ["anomaly_detection", "service_lifecycle", "six_feature_window"],
            },
        },
    )
    conversation.save(update_fields=["updated_at"])
    return message


class AssistantConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.organization_id = str(self.scope["url_route"]["kwargs"]["organization_id"])
        self.conversation_id = str(self.scope["url_route"]["kwargs"]["conversation_id"])
        query = parse_qs(self.scope.get("query_string", b"").decode("utf-8"))
        token = (query.get("ticket") or [""])[0]
        if not token:
            await self.close(code=4401)
            return
        user_id = await authenticate_ticket(token, self.organization_id, self.conversation_id)
        if not user_id:
            await self.close(code=4401)
            return
        self.user_id = user_id
        self.conversation = await load_conversation(
            self.conversation_id, self.organization_id, self.user_id
        )
        if self.conversation is None:
            await self.close(code=4403)
            return
        await self.accept()

    async def receive_json(self, content, **kwargs):
        if content.get("type") != "user_message":
            await self._error("invalid_event", "Only user_message events are accepted.", False)
            return
        text = str(content.get("text", "")).strip()
        if not text or len(text) > 2000:
            await self._error(
                "invalid_message", "Message must contain between 1 and 2,000 characters.", False
            )
            return
        try:
            client_message_id = uuid.UUID(str(content.get("client_message_id", "")))
        except ValueError:
            await self._error("invalid_message_id", "A valid client_message_id is required.", False)
            return

        user_message, created = await persist_user_message(
            self.conversation, client_message_id, text
        )
        await self.send_json({"type": "message_ack", "message": present_message(user_message)})

        if not created:
            response = await existing_assistant_response(self.conversation, client_message_id)
            if response:
                await self.send_json(
                    {
                        "type": "generation_completed",
                        "message": present_message(response),
                        "model": response.evidence.get("model", settings.GEMINI_MODEL),
                        "citations": response.evidence.get("citations", []),
                    }
                )
                return

        evidence = anomaly_evidence_snapshot(self.conversation.anomaly)
        await self.send_json({"type": "generation_started", "client_message_id": str(client_message_id)})
        for citation in ["anomaly_detection", "service_lifecycle", "six_feature_window"]:
            await self.send_json({"type": "citation", "citation": citation})

        history = await recent_messages(self.conversation)
        contents = gemini_contents(evidence, history)
        chunks = []
        try:
            async with asyncio.timeout(settings.GEMINI_REQUEST_TIMEOUT_SECONDS):
                async for delta in stream_gemini_response(contents):
                    chunks.append(delta)
                    await self.send_json({"type": "token_delta", "delta": delta})
            answer = "".join(chunks).strip()
            if not answer:
                raise RuntimeError("empty_gemini_response")
            assistant_message = await persist_assistant_message(
                self.conversation, client_message_id, answer, evidence
            )
            await self.send_json(
                {
                    "type": "generation_completed",
                    "message": present_message(assistant_message),
                    "model": settings.GEMINI_MODEL,
                    "citations": assistant_message.evidence["citations"],
                }
            )
        except asyncio.TimeoutError:
            logger.warning("Gemini request timed out conversation_id=%s", self.conversation_id)
            await self._error("provider_timeout", "The AI response timed out. Please retry.", True)
        except RuntimeError as exc:
            if str(exc) == "gemini_not_configured":
                await self._error(
                    "gemini_not_configured",
                    "Gemini is not configured on the server.",
                    False,
                )
            else:
                logger.exception("Gemini generation failed conversation_id=%s", self.conversation_id)
                await self._error("provider_error", "The AI service is unavailable. Please retry.", True)
        except Exception:
            logger.exception("Gemini generation failed conversation_id=%s", self.conversation_id)
            await self._error("provider_error", "The AI service is unavailable. Please retry.", True)

    async def _error(self, code, message, retryable):
        await self.send_json(
            {
                "type": "generation_error",
                "code": code,
                "message": message,
                "retryable": retryable,
            }
        )
