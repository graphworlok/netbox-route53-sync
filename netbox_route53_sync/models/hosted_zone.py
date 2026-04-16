from django.db import models
from django.urls import reverse
from netbox.models import NetBoxModel

from ..choices import ZoneTypeChoices


class HostedZone(NetBoxModel):
    """
    One Route53 hosted zone.

    The zone_id is the AWS identifier extracted from the JSON filename
    (e.g. 'Z1D633PJN98FT9').  The zone name (e.g. 'example.com.') is
    inferred from the SOA or NS apex record inside the zone file — it is
    not present in the list-resource-record-sets output itself.

    is_private is not available from list-resource-record-sets output; it
    defaults to None (unknown) and can be set manually or via a future
    enrichment source.
    """

    account = models.ForeignKey(
        "netbox_route53_sync.AWSAccount",
        on_delete=models.CASCADE,
        related_name="hosted_zones",
        verbose_name="AWS Account",
    )
    zone_id = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        verbose_name="Zone ID",
        help_text="AWS hosted zone identifier (derived from the JSON filename).",
    )
    name = models.CharField(
        max_length=253,
        db_index=True,
        verbose_name="Zone Name",
        help_text=(
            "DNS zone apex name with trailing dot (e.g. 'example.com.'). "
            "Inferred from the SOA/NS record at the apex of the zone file."
        ),
    )
    zone_type = models.CharField(
        max_length=10,
        choices=ZoneTypeChoices,
        default=ZoneTypeChoices.PUBLIC,
        verbose_name="Type",
        help_text=(
            "Public or Private. Not available from list-resource-record-sets; "
            "defaults to Public and can be set manually."
        ),
    )
    record_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Record Count",
        help_text="Number of resource record sets in the last import.",
    )
    comment = models.TextField(
        blank=True,
        verbose_name="Comment",
    )
    last_synced_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Last Synced",
    )

    class Meta:
        ordering = ["name", "zone_id"]
        verbose_name = "Hosted Zone"
        verbose_name_plural = "Hosted Zones"
        unique_together = [("account", "zone_id")]

    def __str__(self) -> str:
        return f"{self.name} ({self.zone_id})"

    def get_absolute_url(self) -> str:
        return reverse("plugins:netbox_route53_sync:hostedzone", args=[self.pk])

    def get_zone_type_color(self) -> str:
        return ZoneTypeChoices.colors.get(self.zone_type, "secondary")

    @property
    def name_without_dot(self) -> str:
        """Zone name with the trailing dot stripped for display."""
        return self.name.rstrip(".")
