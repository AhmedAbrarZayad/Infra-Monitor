import hashlib
import secrets
from datetime import timedelta
from django.conf import settings
from django.utils import timezone



class TokenService:

    @staticmethod
    def generate_enrollment_token():
        """
        Generates a cryptographically secure, URL-safe enrollment token 
        and its expiration timestamp.
        """
        # 1. Generate 32 bytes of secure random data, encoded as URL-safe base64.
        # (This results in a 43-character random string)
        raw_token = secrets.token_urlsafe(32)
        
        # 2. Add a prefix so it's easily identifiable in logs and the database
        token_string = f"enroll_{raw_token}"
        
        # 3. Calculate the expiration time (e.g., 15 minutes from now)
        # Always use timezone.now() in Django to ensure timezone-aware datetimes
        expires_at = timezone.now() + timedelta(
            minutes=getattr(settings, "MONITORING_ENROLLMENT_EXPIRY_MINUTES", 15)
        )
        
        return token_string, expires_at

    @staticmethod
    def hash_enrollment_token(raw_token):
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
