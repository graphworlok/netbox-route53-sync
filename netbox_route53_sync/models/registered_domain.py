from django.db import models
from django.urls import reverse
from netbox.models import NetBoxModel


class RegisteredDomain(NetBoxModel):
    """
    One entry from Registered_Domains.json (aws route53domains list-domains).

    AWS list-domains output structure:
    {
        "Domains": [
            {
                "DomainName":    "example.com",
                "AutoRenew":     true,
                "TransferLock":  true,
                "Expiry":        "2027-03-15T00:00:00Z"
            },
            ...
        ]
    }

    There is no hosted zone ID in this output.  The link to a HostedZone is
    made at import time by matching DomainName against zone names (with the
    trailing dot stripped).
    """

    account = models.ForeignKey(
        "netbox_route53_sync.AWSAccount",
        on_delete=models.CASCADE,
        related_name="registered_domains",
        verbose_name="AWS Account",
    )
    domain_name = models.CharField(
        max_length=253,
        db_index=True,
        verbose_name="Domain Name",
        help_text="DomainName from list-domains output.",
    )
    auto_renew = models.BooleanField(
        default=True,
        verbose_name="Auto Renew",
        help_text="AutoRenew from list-domains output.",
    )
    transfer_lock = models.BooleanField(
        default=True,
        verbose_name="Transfer Lock",
        help_text="TransferLock from list-domains output.",
    )
    expiry = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Expiry",
        help_text="Expiry from list-domains output.",
    )

    # Linked hosted zone — set when a zone with a matching name is found
    hosted_zone = models.ForeignKey(
        "netbox_route53_sync.HostedZone",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="registered_domains",
        verbose_name="Hosted Zone",
        help_text=(
            "Hosted zone whose apex name matches this domain. "
            "Set automatically at sync time."
        ),
    )

    last_synced_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Last Synced",
    )

    class Meta:
        ordering = ["domain_name"]
        verbose_name = "Registered Domain"
        verbose_name_plural = "Registered Domains"
        unique_together = [("account", "domain_name")]

    def __str__(self) -> str:
        return self.domain_name

    def get_absolute_url(self) -> str:
        return reverse("plugins:netbox_route53_sync:registereddomain", args=[self.pk])

    @property
    def is_expired(self) -> bool:
        from django.utils import timezone
        if self.expiry is None:
            return False
        return self.expiry < timezone.now()
