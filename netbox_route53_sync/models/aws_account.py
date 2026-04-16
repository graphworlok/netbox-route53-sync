from django.db import models
from django.urls import reverse
from netbox.models import NetBoxModel


class AWSAccount(NetBoxModel):
    """
    Represents one AWS account folder under the data root.

    The account_id is the numeric AWS account ID (the folder name).
    The label is an optional human-friendly name for display.
    """

    account_id = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        verbose_name="Account ID",
        help_text="Numeric AWS account ID (matches the folder name under data_root).",
    )
    label = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Label",
        help_text="Optional human-friendly name for this AWS account.",
    )
    last_synced_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Last Synced",
    )

    class Meta:
        ordering = ["account_id"]
        verbose_name = "AWS Account"
        verbose_name_plural = "AWS Accounts"

    def __str__(self) -> str:
        return self.label or self.account_id

    def get_absolute_url(self) -> str:
        return reverse("plugins:netbox_route53_sync:awsaccount", args=[self.pk])

    @property
    def display_name(self) -> str:
        if self.label:
            return f"{self.label} ({self.account_id})"
        return self.account_id
