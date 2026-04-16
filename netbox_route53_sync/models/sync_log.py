from django.db import models
from django.urls import reverse

from ..choices import SyncStatusChoices


class SyncLog(models.Model):
    """
    Audit record for a single sync run.  One record is created per AWS account
    per run.  Plain Django model — not user-editable.
    """

    account_id    = models.CharField(max_length=20, db_index=True)
    account_label = models.CharField(max_length=200, blank=True)

    started_at   = models.DateTimeField(auto_now_add=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    status  = models.CharField(
        max_length=20,
        choices=SyncStatusChoices,
        default=SyncStatusChoices.PENDING,
        db_index=True,
    )
    message = models.TextField(blank=True)

    # Registered domains
    domains_seen    = models.PositiveIntegerField(default=0)
    domains_created = models.PositiveIntegerField(default=0)
    domains_updated = models.PositiveIntegerField(default=0)

    # Hosted zones
    zones_seen    = models.PositiveIntegerField(default=0)
    zones_created = models.PositiveIntegerField(default=0)
    zones_updated = models.PositiveIntegerField(default=0)

    # Zone records
    records_seen    = models.PositiveIntegerField(default=0)
    records_created = models.PositiveIntegerField(default=0)
    records_updated = models.PositiveIntegerField(default=0)
    records_deleted = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-started_at"]
        verbose_name = "Sync Log"
        verbose_name_plural = "Sync Logs"

    def __str__(self) -> str:
        label = self.account_label or self.account_id
        return f"{label} @ {self.started_at:%Y-%m-%d %H:%M}"

    def get_absolute_url(self) -> str:
        return reverse("plugins:netbox_route53_sync:synclog", args=[self.pk])

    @property
    def duration(self):
        if self.completed_at and self.started_at:
            return self.completed_at - self.started_at
        return None

    def get_status_color(self) -> str:
        return SyncStatusChoices.colors.get(self.status, "secondary")
