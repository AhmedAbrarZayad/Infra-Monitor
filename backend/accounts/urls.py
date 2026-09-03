from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from accounts.views import (
    RegisterView,
    VerifyEmailView,
    ResendOTPView,
    LoginView,
    LogoutView,
    ForgotPasswordView,
    ResetPasswordView,
    MeView,
)
app_name = "accounts"

urlpatterns = [
    # Registration & email verification
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("verify-email/", VerifyEmailView.as_view(), name="auth-verify-email"),
    path("resend-otp/", ResendOTPView.as_view(), name="auth-resend-otp"),
    # Login & logout
    path("login/", LoginView.as_view(), name="auth-login"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    # Password reset
    path("forgot-password/", ForgotPasswordView.as_view(), name="auth-forgot-password"),
    path("reset-password/", ResetPasswordView.as_view(), name="auth-reset-password"),
    # JWT token refresh
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("me/", MeView.as_view(), name="me"),
]
