import uuid
from urllib.parse import quote

from django.conf import settings
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from ai.models import AssistantConversation, AssistantMessage
from ai.presenters import present_assistant_anomaly, present_conversation, present_message
from ai.services import issue_websocket_ticket
from ai.throttles import AssistantTicketThrottle
from common.api import get_organization_membership, paginated_response
from common.authorization import anomalies_visible_to


SUGGESTED_PROMPTS = [
    "Explain what is unusual in these metrics.",
    "What should I check first?",
    "What are the likely causes?",
    "Which metric is the strongest signal?",
    "Give me a safe diagnostic checklist.",
]


def parse_uuid(value, field_name):
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        raise ValidationError({field_name: "A valid UUID is required."}) from None


def anomaly_queryset(membership):
    return (
        anomalies_visible_to(membership).filter(is_anomaly=True)
        .select_related("server_id", "service_id")
        .order_by("-detected_at", "detection_id")
    )


class AssistantContextView(APIView):
    def get(self, request, organization_id):
        _, membership = get_organization_membership(request, organization_id)
        anomalies = list(anomaly_queryset(membership)[:20])
        selected = None
        requested_id = request.query_params.get("anomaly_id")
        if requested_id:
            selected_id = parse_uuid(requested_id, "anomaly_id")
            selected = get_object_or_404(anomaly_queryset(membership), pk=selected_id)
            if all(item.pk != selected.pk for item in anomalies):
                anomalies.insert(0, selected)
        elif anomalies:
            selected = anomalies[0]
        return Response(
            {
                "anomalies": [present_assistant_anomaly(item) for item in anomalies],
                "selected_anomaly": present_assistant_anomaly(selected) if selected else None,
                "suggested_prompts": SUGGESTED_PROMPTS,
                "gemini_configured": bool(settings.GEMINI_API_KEY),
            }
        )


class AssistantConversationCollectionView(APIView):
    def post(self, request, organization_id):
        organization, membership = get_organization_membership(request, organization_id)
        anomaly_id = parse_uuid(request.data.get("anomaly_id"), "anomaly_id")
        anomaly = get_object_or_404(anomaly_queryset(membership), pk=anomaly_id)
        service_name = anomaly.service_id.display_name if anomaly.service_id else "Unknown service"
        defaults = {"title": f"Anomaly: {service_name}"}
        try:
            with transaction.atomic():
                conversation, created = AssistantConversation.objects.get_or_create(
                    organization=organization,
                    user_id=request.user,
                    anomaly=anomaly,
                    defaults=defaults,
                )
        except IntegrityError:
            conversation = AssistantConversation.objects.get(
                organization=organization, user_id=request.user, anomaly=anomaly
            )
            created = False
        return Response(
            present_conversation(conversation),
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


def owned_conversation(request, organization, membership, conversation_id):
    return get_object_or_404(
        AssistantConversation.objects.select_related("anomaly"),
        pk=conversation_id,
        organization=organization,
        user_id=request.user,
        anomaly__is_anomaly=True,
        anomaly__in=anomalies_visible_to(membership),
    )


class AssistantMessageListView(APIView):
    def get(self, request, organization_id, conversation_id):
        organization, membership = get_organization_membership(request, organization_id)
        conversation = owned_conversation(request, organization, membership, conversation_id)
        queryset = AssistantMessage.objects.filter(conversation_id=conversation)
        return paginated_response(request, queryset, present_message)


class AssistantWebSocketTicketView(APIView):
    throttle_classes = [AssistantTicketThrottle]

    def post(self, request, organization_id):
        organization, membership = get_organization_membership(request, organization_id)
        conversation_id = parse_uuid(request.data.get("conversation_id"), "conversation_id")
        conversation = owned_conversation(request, organization, membership, conversation_id)
        token, ticket = issue_websocket_ticket(
            organization=organization,
            user=request.user,
            conversation=conversation,
        )
        path = (
            f"/ws/organizations/{organization.pk}/assistant/conversations/"
            f"{conversation.pk}/?ticket={quote(token)}"
        )
        return Response(
            {
                "ticket": token,
                "expires_at": ticket.expires_at,
                "websocket_path": path,
            },
            status=status.HTTP_201_CREATED,
        )
