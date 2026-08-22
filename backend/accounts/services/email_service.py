import base64
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from django.conf import settings
from django.template.loader import render_to_string
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

logger = logging.getLogger(__name__)

# Google OAuth2 token endpoint
GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"


class GmailOAuth2EmailService:
    """Send emails via Gmail SMTP using OAuth 2.0 (XOAUTH2 mechanism)."""

    def __init__(self):
        self.sender_email = settings.GMAIL_SENDER_EMAIL
        self.client_id = settings.GMAIL_CLIENT_ID
        self.client_secret = settings.GMAIL_CLIENT_SECRET
        self.refresh_token = settings.GMAIL_REFRESH_TOKEN

    def _get_access_token(self) -> str:
        """Obtain a fresh access token using the stored refresh token."""
        credentials = Credentials(
            token=None,
            refresh_token=self.refresh_token,
            client_id=self.client_id,
            client_secret=self.client_secret,
            token_uri=GOOGLE_TOKEN_URI,
        )
        credentials.refresh(Request())
        return credentials.token

    def _generate_xoauth2_string(self, access_token: str) -> str:
        """Generate the XOAUTH2 authentication string for SMTP."""
        auth_string = f"user={self.sender_email}\x01auth=Bearer {access_token}\x01\x01"
        return base64.b64encode(auth_string.encode("utf-8")).decode("utf-8")

    def send_email(self, to: str, subject: str, html_body: str) -> bool:
        """
        Connect to smtp.gmail.com:587, STARTTLS, AUTH XOAUTH2, and send.

        Returns True on success, False on failure.
        """
        try:
            access_token = self._get_access_token()
            xoauth2_string = self._generate_xoauth2_string(access_token)

            msg = MIMEMultipart("alternative")
            msg["From"] = f"Infra Monitor <{self.sender_email}>"
            msg["To"] = to
            msg["Subject"] = subject
            msg.attach(MIMEText(html_body, "html"))

            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.docmd("AUTH", f"XOAUTH2 {xoauth2_string}")
                server.sendmail(self.sender_email, [to], msg.as_string())

            logger.info("Email sent successfully to %s", to)
            return True

        except Exception:
            logger.exception("Failed to send email to %s", to)
            return False

    def send_welcome_email(self, user) -> bool:
        """Send a branded welcome email after registration."""
        html_body = render_to_string(
            "emails/welcome.html",
            {
                "user": user,
                "app_name": "Infra Monitor",
            },
        )
        return self.send_email(
            to=user.email,
            subject="Welcome to Infra Monitor! 🚀",
            html_body=html_body,
        )

    def send_email_verification_otp(self, user, otp: str) -> bool:
        """Send an OTP code for email verification."""
        html_body = render_to_string(
            "emails/email_verification_otp.html",
            {
                "user": user,
                "otp": otp,
                "expiry_minutes": settings.OTP_EXPIRY_MINUTES,
                "app_name": "Infra Monitor",
            },
        )
        return self.send_email(
            to=user.email,
            subject=f"Your Verification Code: {otp}",
            html_body=html_body,
        )

    def send_password_reset_otp(self, user, otp: str) -> bool:
        """Send an OTP code for password reset."""
        html_body = render_to_string(
            "emails/password_reset_otp.html",
            {
                "user": user,
                "otp": otp,
                "expiry_minutes": settings.OTP_EXPIRY_MINUTES,
                "app_name": "Infra Monitor",
            },
        )
        return self.send_email(
            to=user.email,
            subject=f"Password Reset Code: {otp}",
            html_body=html_body,
        )
