from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from accounts.serializers import present_user

UNSET = object()


def user_id_value(data, field, *, optional=False):
    if optional and field not in data:
        return UNSET
    value = data.get(field)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValidationError({field: "Use a user ID or null."}) from None


def assignment_action(previous_id, new_id):
    if previous_id is None:
        return "ASSIGNED"
    if new_id is None:
        return "UNASSIGNED"
    return "REASSIGNED"


def assignment_conflict(current_user):
    return Response(
        {
            "detail": "The assignment changed after it was loaded.",
            "code": "assignment_changed",
            "assigned_to": present_user(current_user),
        },
        status=409,
    )
