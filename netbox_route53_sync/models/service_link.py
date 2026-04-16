from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse
from netbox.models import NetBoxModel

from ..choices import ServiceLinkRoleChoices


# The set of Route53 models that a ServiceLink may be attached to.
# Used for validation in forms and for UI display.
LINKABLE_MODELS = (
    "netbox_route53_sync.awsaccount",
    "netbox_route53_sync.hostedzone",
    "netbox_route53_sync.registereddomain",
    "netbox_route53_sync.zonerecord",
)


class ServiceLink(NetBoxModel):
    """
    Associates a Route53 object (AWSAccount, HostedZone, RegisteredDomain,
    or ZoneRecord) with a NetBox ipam.Service.

    The generic FK allows one table to cover all object types rather than
    requiring a separate association table per model.

    Typical uses:
      - Link a RegisteredDomain to the Service it supports
        (role: "serves" or "technical-owner")
      - Link a HostedZone to the team responsible for it
        (role: "managed-by")
      - Link a ZoneRecord to the service it routes traffic to
        (role: "serves")
    """

    # --- Generic FK to the Route53 object ---
    assigned_object_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to=models.Q(
            app_label="netbox_route53_sync",
            model__in=("awsaccount", "hostedzone", "registereddomain", "zonerecord"),
        ),
        related_name="+",
        verbose_name="Object Type",
    )
    assigned_object_id = models.PositiveBigIntegerField(
        verbose_name="Object ID",
    )
    assigned_object = GenericForeignKey(
        ct_field="assigned_object_type",
        fk_field="assigned_object_id",
    )

    # --- NetBox Service ---
    service = models.ForeignKey(
        "ipam.Service",
        on_delete=models.CASCADE,
        related_name="route53_links",
        verbose_name="Service",
    )

    # --- Relationship metadata ---
    role = models.CharField(
        max_length=30,
        choices=ServiceLinkRoleChoices,
        default=ServiceLinkRoleChoices.OTHER,
        verbose_name="Role",
        help_text="Nature of the relationship between the Route53 object and the service.",
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Notes",
    )

    class Meta:
        ordering = ["assigned_object_type", "assigned_object_id", "role"]
        verbose_name = "Service Link"
        verbose_name_plural = "Service Links"
        indexes = [
            models.Index(
                fields=["assigned_object_type", "assigned_object_id"],
                name="route53_servicelink_object_idx",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.assigned_object} → {self.service} "
            f"({self.get_role_display()})"
        )

    def get_absolute_url(self) -> str:
        return reverse("plugins:netbox_route53_sync:servicelink", args=[self.pk])

    def get_role_color(self) -> str:
        return ServiceLinkRoleChoices.colors.get(self.role, "secondary")
