from rest_framework.throttling import UserRateThrottle


class AssistantTicketThrottle(UserRateThrottle):
    scope = "assistant_ticket"
