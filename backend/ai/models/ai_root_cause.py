from django.db import models
from .ai_analysis import AiAnalysis

class AiRootCause(models.Model):
    root_cause_id = models.UUIDField(primary_key=True)
    analysis_id = models.ForeignKey(AiAnalysis, on_delete=models.CASCADE)
    cause_text = models.CharField()
    confidence_score = models.FloatField()
    rank_order = models.IntegerField()