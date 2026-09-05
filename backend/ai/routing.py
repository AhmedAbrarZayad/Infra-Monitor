from django.urls import re_path

from ai.consumers import AssistantConsumer


websocket_urlpatterns = [
    re_path(
        r"^ws/organizations/(?P<organization_id>[0-9a-f-]+)/assistant/conversations/"
        r"(?P<conversation_id>[0-9a-f-]+)/$",
        AssistantConsumer.as_asgi(),
    )
]
