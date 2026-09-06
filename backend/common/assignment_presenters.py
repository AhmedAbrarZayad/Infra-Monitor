from accounts.serializers import present_user

_UNSET = object()


def present_assignment_event(event, resource_type, actor=_UNSET):
    resolved_actor = event.actor if actor is _UNSET else actor
    return {
        "id": event.pk,
        "resource_type": resource_type,
        "action": event.action,
        "actor": present_user(resolved_actor),
        "previous_subject": present_user(event.previous_subject),
        "new_subject": present_user(event.new_subject),
        "created_at": event.created_at,
    }
