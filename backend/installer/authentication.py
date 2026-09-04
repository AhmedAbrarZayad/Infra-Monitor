from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from servers.services import MonitoringCredentialService


class ServerCredentialAuthentication(BaseAuthentication):
    """Authenticate Alloy using its write-only server credential."""

    keyword = "Bearer"

    def authenticate(self, request):
        header = request.headers.get("Authorization", "")
        parts = header.split()
        if len(parts) != 2 or parts[0].lower() != self.keyword.lower():
            raise AuthenticationFailed("Invalid server credential.")

        credential = MonitoringCredentialService.verify(parts[1])
        if credential is None:
            raise AuthenticationFailed("Invalid server credential.")

        # These endpoints do not act as a user. DRF stores the authenticated
        # credential in request.auth and the views derive identity from it.
        return None, credential

    def authenticate_header(self, request):
        return self.keyword
