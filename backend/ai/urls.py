from django.urls import path

from ai.views import (
    AssistantContextView,
    AssistantConversationCollectionView,
    AssistantMessageListView,
    AssistantWebSocketTicketView,
)


app_name = "assistant"
urlpatterns = [
    path("assistant/context/", AssistantContextView.as_view(), name="context"),
    path(
        "assistant/conversations/",
        AssistantConversationCollectionView.as_view(),
        name="conversations",
    ),
    path(
        "assistant/conversations/<uuid:conversation_id>/messages/",
        AssistantMessageListView.as_view(),
        name="messages",
    ),
    path(
        "assistant/websocket-tickets/",
        AssistantWebSocketTicketView.as_view(),
        name="websocket-ticket",
    ),
]
