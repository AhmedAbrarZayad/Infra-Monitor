from rest_framework.permissions import BasePermission


class IsEmailVerified(BasePermission):
    message = "A verified email address is required."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_email_verified)
