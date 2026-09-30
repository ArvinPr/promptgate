from django.db import models

from accounts.models import APIKey


class GenerationUsage(models.Model):
    class Status(models.TextChoices):
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    request_id = models.CharField(max_length=64, unique=True)
    api_key = models.ForeignKey(
        APIKey,
        on_delete=models.PROTECT,
        related_name="generation_usages",
    )
    provider = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    input_tokens = models.PositiveIntegerField(null=True, blank=True)
    output_tokens = models.PositiveIntegerField(null=True, blank=True)
    total_tokens = models.PositiveIntegerField(null=True, blank=True)
    latency_ms = models.PositiveIntegerField()
    status = models.CharField(max_length=10, choices=Status.choices)
    error_category = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
