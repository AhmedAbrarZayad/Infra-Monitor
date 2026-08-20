from django.db import models
from .ai_analysis import AiAnalysis
class AiRecommendation(models.Model):
    recommendation_id = models.UUIDField(primary_key=True)
    analysis_id = models.ForeignKey(AiAnalysis, on_delete=models.CASCADE)
    action_text = models.CharField()
    risk_level = models.IntegerField()
    is_completed = models.BooleanField()