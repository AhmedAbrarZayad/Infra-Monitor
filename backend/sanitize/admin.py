from django.contrib import admin

from sanitize.models import RequestLog, ShieldConfig, ThreatSuggestion

admin.site.register(RequestLog)
admin.site.register(ShieldConfig)
admin.site.register(ThreatSuggestion)
