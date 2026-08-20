from django.db import models
from .ai_analysis import AiAnalysis
from log.models.log_entry import LogEntry
class AiLogFinding(models.Model):
    finding_id = models.UUIDField(primary_key=True)
    analysis_id = models.ForeignKey(AiAnalysis, on_delete=models.CASCADE)
    log_id = models.ForeignKey(LogEntry, on_delete=models.CASCADE, null=True)
    relevance_score = models.FloatField()
    explanation = models.CharField()