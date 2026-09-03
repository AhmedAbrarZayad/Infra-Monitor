import hashlib
import secrets
import uuid

from django.db.models import Q
from django.utils import timezone

from servers.models.monitoring import ServerWriteCredential


class MonitoringCredentialService:
    PREFIX = "srv"

    @classmethod
    def issue(cls, connection, actor=None, rotation_key=None):
        credential_id = uuid.uuid4()
        secret = secrets.token_urlsafe(32)
        raw = f"{cls.PREFIX}_{credential_id.hex}.{secret}"
        credential = ServerWriteCredential.objects.create(
            id=credential_id,
            connection=connection,
            secret_hash=hashlib.sha256(secret.encode("utf-8")).hexdigest(),
            created_by=actor,
            rotation_key=rotation_key,
        )
        return credential, raw

    @classmethod
    def verify(cls, raw):
        try:
            public, secret = raw.split(".", 1)
            prefix, identifier = public.split("_", 1)
            if prefix != cls.PREFIX:
                return None
            credential = ServerWriteCredential.objects.select_related("connection__server").get(id=uuid.UUID(hex=identifier))
        except (ValueError, ServerWriteCredential.DoesNotExist):
            return None
        now = timezone.now()
        usable = credential.state == ServerWriteCredential.State.ACTIVE or (
            credential.state == ServerWriteCredential.State.GRACE
            and credential.valid_until is not None
            and credential.valid_until > now
        )
        expected = hashlib.sha256(secret.encode("utf-8")).hexdigest()
        if not usable or not secrets.compare_digest(expected, credential.secret_hash):
            return None
        return credential

    @staticmethod
    def revoke_all(connection, at=None):
        at = at or timezone.now()
        return connection.credentials.filter(Q(state="ACTIVE") | Q(state="GRACE")).update(
            state="REVOKED", revoked_at=at, valid_until=at
        )
