from django.db import models
from django.urls import reverse
from netbox.models import NetBoxModel

from ..choices import RecordTypeChoices


class ZoneRecord(NetBoxModel):
    """
    One ResourceRecordSet from a Route53 hosted zone.

    AWS returns two mutually exclusive forms per record:

    Standard record
        "ResourceRecords": [{"Value": "..."}, ...]   — one or more values
        "TTL": 300

    Alias record
        "AliasTarget": {
            "HostedZoneId":          "Z2FDTNDATAQYW2",
            "DNSName":               "d111111abcdef8.cloudfront.net.",
            "EvaluateTargetHealth":  false
        }
        (No TTL, no ResourceRecords)

    For standard records, all values are stored as a JSON list in `values`.
    For alias records, the AliasTarget fields are stored in the alias_* columns
    and `is_alias` is True.
    """

    zone = models.ForeignKey(
        "netbox_route53_sync.HostedZone",
        on_delete=models.CASCADE,
        related_name="records",
        verbose_name="Hosted Zone",
    )
    name = models.CharField(
        max_length=253,
        db_index=True,
        verbose_name="Name",
        help_text="DNS record name as returned by AWS (trailing dot included).",
    )
    record_type = models.CharField(
        max_length=10,
        choices=RecordTypeChoices,
        db_index=True,
        verbose_name="Type",
    )
    ttl = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name="TTL",
        help_text="Time-to-live in seconds. Null for alias records.",
    )

    # --- Standard record values ---
    values = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Values",
        help_text=(
            "List of record values from ResourceRecords[].Value. "
            "Empty for alias records."
        ),
    )

    # --- Alias record fields ---
    is_alias = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name="Alias",
        help_text="True when the record is a Route53 alias (AliasTarget).",
    )
    alias_dns_name = models.CharField(
        max_length=253,
        blank=True,
        verbose_name="Alias DNS Name",
        help_text="AliasTarget.DNSName — the target of the alias.",
    )
    alias_hosted_zone_id = models.CharField(
        max_length=64,
        blank=True,
        verbose_name="Alias Hosted Zone ID",
        help_text="AliasTarget.HostedZoneId — the zone that owns the alias target.",
    )
    alias_evaluate_target_health = models.BooleanField(
        null=True, blank=True,
        verbose_name="Evaluate Target Health",
        help_text="AliasTarget.EvaluateTargetHealth.",
    )

    # --- Optional cross-reference to a NetBox IPAddress ---
    linked_ip = models.ForeignKey(
        "ipam.IPAddress",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="route53_records",
        verbose_name="Linked IP",
        help_text=(
            "NetBox IPAddress that matches the first A/AAAA value. "
            "Populated automatically when link_ip_addresses is True."
        ),
    )

    class Meta:
        ordering = ["zone", "name", "record_type"]
        verbose_name = "Zone Record"
        verbose_name_plural = "Zone Records"

    def __str__(self) -> str:
        return f"{self.name} {self.record_type}"

    def get_absolute_url(self) -> str:
        return reverse("plugins:netbox_route53_sync:zonerecord", args=[self.pk])

    def get_record_type_color(self) -> str:
        return RecordTypeChoices.colors.get(self.record_type, "secondary")

    @property
    def name_without_dot(self) -> str:
        return self.name.rstrip(".")

    @property
    def display_values(self) -> list[str]:
        """Return alias target or record values for uniform display."""
        if self.is_alias:
            return [f"ALIAS → {self.alias_dns_name}"]
        return self.values
