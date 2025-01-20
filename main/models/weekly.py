from django.db import models

from main.models.base import BaseModel


class WeeklyStats(BaseModel):
    env = models.CharField(max_length=10)
    week_start_date = models.CharField(max_length=20)
    week_end_date = models.CharField(max_length=20)
    counts = models.JSONField()
    rates = models.JSONField()
    labels = models.JSONField()

    class Meta:
        db_table = "weekly_stats"
        verbose_name = "每周统计"
        verbose_name_plural = "每周统计"

