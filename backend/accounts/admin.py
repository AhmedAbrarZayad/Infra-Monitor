from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts.models import Users, UserPreference, PasswordResetOTP, EmailVerificationOTP


@admin.register(Users)
class CustomUserAdmin(UserAdmin):
    list_display = ("email", "username", "role", "is_email_verified", "is_active", "created_at")
    list_filter = ("is_email_verified", "is_active", "role")
    search_fields = ("email", "username", "first_name", "last_name")
    ordering = ("-created_at",)

    fieldsets = UserAdmin.fieldsets + (
        ("Infra Monitor", {"fields": ("role", "is_email_verified")}),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Infra Monitor", {"fields": ("email", "role")}),
    )


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user_id", "notifications_enabled", "refresh_interval_seconds", "updated_at")


@admin.register(PasswordResetOTP)
class PasswordResetOTPAdmin(admin.ModelAdmin):
    list_display = ("user", "otp", "created_at", "expires_at", "is_used")
    list_filter = ("is_used",)
    search_fields = ("user__email",)
    readonly_fields = ("id", "otp", "created_at")


@admin.register(EmailVerificationOTP)
class EmailVerificationOTPAdmin(admin.ModelAdmin):
    list_display = ("user", "otp", "created_at", "expires_at", "is_used")
    list_filter = ("is_used",)
    search_fields = ("user__email",)
    readonly_fields = ("id", "otp", "created_at")
