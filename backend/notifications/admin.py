from django.contrib import admin

from .models import DeviceRegistration, SentNotification


@admin.register(DeviceRegistration)
class DeviceRegistrationAdmin(admin.ModelAdmin):
    list_display = ("user", "installation_id", "active", "last_seen_at")
    exclude = ("token",)


@admin.register(SentNotification)
class SentNotificationAdmin(admin.ModelAdmin):
    list_display = ("event_type", "user", "organization", "state", "created_at")
    readonly_fields = ("provider_message_id", "provider_error")
