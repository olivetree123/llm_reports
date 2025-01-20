from django.db import models

from main.models.base import BaseModel


class DailyStats(BaseModel):
    env = models.CharField(max_length=10)
    date = models.CharField(max_length=20)
    counts = models.JSONField()
    rates = models.JSONField()
    labels = models.JSONField()

    class Meta:
        db_table = "daily_stats"
        verbose_name = "每日统计"
        verbose_name_plural = "每日统计"

