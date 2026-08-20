from django.db import models
from accounts.models.users import Users


class Servers(models.Model):
    server_id = models.UUIDField(primary_key=True)
    name = models.CharField()
    host_name = models.CharField()
    ip_address = models.CharField()
    environment = models.CharField()
    os_type = models.CharField()
    status = models.CharField()
    agent_config = models.JSONField()
    last_seen_at = models.DateTimeField()
    registered_at = models.DateTimeField()
    registered_by = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True)