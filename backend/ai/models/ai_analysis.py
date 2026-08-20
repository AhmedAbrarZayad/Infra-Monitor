from django.db import models
from incident.models.incident import Incident
class AiAnalysis(models.Model):
    analysis_id = models.UUIDField(primary_key=True)
    incident_id = models.ForeignKey(Incident, on_delete=models.SET_NULL, null=True)
    summary = models.CharField()
    explanation = models.CharField()
    confidence_score = models.FloatField()
    created_at = models.DateTimeField()