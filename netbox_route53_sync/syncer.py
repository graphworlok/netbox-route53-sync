"""
Route53 → NetBox ORM syncer.

Takes ParsedAccount objects from reader.py and writes them to NetBox using
the Django ORM.  All database writes for a single account run inside an
atomic transaction; a failure on one zone does not roll back the domains or
other zones already committed.

What is created / updated
--------------------------
netbox_route53_sync.AWSAccount       — created on first sync, updated thereafter
netbox_route53_sync.RegisteredDomain — upserted by (account, domain_name)
netbox_route53_sync.HostedZone       — upserted by zone_id
netbox_route53_sync.ZoneRecord       — full replace per zone on each sync:
                                       existing records for a zone are deleted
                                       and replaced with the current file content.
                                       This is safe because route53 is the source
                                       of truth — manual edits should not be made
                                       directly to ZoneRecord rows.
ipam.IPAddress                       — read-only cross-reference; never created
                                       or modified by this syncer.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from django.db import transaction

from .models import AWSAccount, HostedZone, RegisteredDomain, SyncLog, ZoneRecord
from .reader import ParsedAccount, ParsedDomain, ParsedRecord, ParsedZone

log = logging.getLogger(__name__)


class Route53Syncer:
    """
    Sync one ParsedAccount into NetBox.

    Usage::

        syncer = Route53Syncer(sync_log=log_obj, dry_run=False, link_ips=True)
        syncer.sync(parsed_account)
        syncer.close()
    """

    def __init__(
        self,
        sync_log: SyncLog,
        *,
        dry_run: bool = False,
        link_ips: bool = True,
    ) -> None:
        self.log      = sync_log
        self.dry_run  = dry_run
        self.link_ips = link_ips

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def sync(self, parsed: ParsedAccount) -> None:
        """Sync the entire ParsedAccount."""
        account = self._upsert_account(parsed.account_id)

        if not self.dry_run:
            self.log.save()

        # Domains
        for domain in parsed.domains:
            try:
                with transaction.atomic():
                    self._sync_domain(domain, account)
            except Exception as exc:
                log.warning("Failed to sync domain %s: %s", domain.domain_name, exc)

        # Zones
        for zone in parsed.zones:
            try:
                with transaction.atomic():
                    self._sync_zone(zone, account)
            except Exception as exc:
                log.warning("Failed to sync zone %s: %s", zone.zone_id, exc)

        # Link domains → zones now that both sides are committed
        if not self.dry_run:
            self._link_domains_to_zones(account)

        # Stamp account last_synced_at
        if not self.dry_run:
            account.last_synced_at = datetime.now(tz=timezone.utc)
            account.save(update_fields=["last_synced_at"])

        # Persist final counters
        if not self.dry_run:
            self.log.save(update_fields=[
                "domains_seen", "domains_created", "domains_updated",
                "zones_seen", "zones_created", "zones_updated",
                "records_seen", "records_created", "records_updated",
                "records_deleted",
            ])

    def close(self, *, success: bool = True, message: str = "") -> None:
        from .choices import SyncStatusChoices
        self.log.completed_at = datetime.now(tz=timezone.utc)
        if success and not message:
            self.log.status = SyncStatusChoices.SUCCESS
        elif success and message:
            self.log.status = SyncStatusChoices.PARTIAL
        else:
            self.log.status = SyncStatusChoices.FAILED
        self.log.message = message
        if not self.dry_run:
            self.log.save()

    # ------------------------------------------------------------------
    # AWSAccount
    # ------------------------------------------------------------------

    def _upsert_account(self, account_id: str) -> AWSAccount:
        if self.dry_run:
            return AWSAccount(account_id=account_id)
        account, created = AWSAccount.objects.get_or_create(
            account_id=account_id,
            defaults={"label": ""},
        )
        return account

    # ------------------------------------------------------------------
    # RegisteredDomain
    # ------------------------------------------------------------------

    def _sync_domain(self, parsed: ParsedDomain, account: AWSAccount) -> None:
        self.log.domains_seen += 1

        if self.dry_run:
            log.info("[dry-run] Domain %s", parsed.domain_name)
            return

        domain, created = RegisteredDomain.objects.get_or_create(
            account     = account,
            domain_name = parsed.domain_name,
            defaults={
                "auto_renew":    parsed.auto_renew,
                "transfer_lock": parsed.transfer_lock,
                "expiry":        parsed.expiry,
                "last_synced_at": datetime.now(tz=timezone.utc),
            },
        )

        if created:
            self.log.domains_created += 1
        else:
            changed = []
            if domain.auto_renew != parsed.auto_renew:
                domain.auto_renew = parsed.auto_renew
                changed.append("auto_renew")
            if domain.transfer_lock != parsed.transfer_lock:
                domain.transfer_lock = parsed.transfer_lock
                changed.append("transfer_lock")
            if domain.expiry != parsed.expiry:
                domain.expiry = parsed.expiry
                changed.append("expiry")
            changed.append("last_synced_at")
            domain.last_synced_at = datetime.now(tz=timezone.utc)
            domain.save(update_fields=changed)
            self.log.domains_updated += 1

    # ------------------------------------------------------------------
    # HostedZone
    # ------------------------------------------------------------------

    def _sync_zone(self, parsed: ParsedZone, account: AWSAccount) -> None:
        self.log.zones_seen += 1

        if self.dry_run:
            log.info(
                "[dry-run] Zone %s (%s) — %d records",
                parsed.zone_id, parsed.name, len(parsed.records),
            )
            self.log.records_seen += len(parsed.records)
            return

        zone, created = HostedZone.objects.get_or_create(
            zone_id = parsed.zone_id,
            defaults={
                "account":      account,
                "name":         parsed.name,
                "record_count": len(parsed.records),
                "last_synced_at": datetime.now(tz=timezone.utc),
            },
        )

        if created:
            self.log.zones_created += 1
        else:
            changed = []
            if zone.name != parsed.name:
                zone.name = parsed.name
                changed.append("name")
            if zone.account_id != account.pk:
                zone.account = account
                changed.append("account")
            if zone.record_count != len(parsed.records):
                zone.record_count = len(parsed.records)
                changed.append("record_count")
            zone.last_synced_at = datetime.now(tz=timezone.utc)
            changed.append("last_synced_at")
            zone.save(update_fields=changed)
            self.log.zones_updated += 1

        # Full replace of records for this zone
        self._replace_zone_records(zone, parsed.records)

    def _replace_zone_records(
        self, zone: HostedZone, records: list[ParsedRecord]
    ) -> None:
        """
        Delete all existing ZoneRecord rows for this zone and recreate from
        the current file content.

        Route53 is the source of truth so a full replace is safe and simpler
        than diffing individual records (which would need to handle multi-value
        records, alias vs standard, etc.).
        """
        deleted_count = ZoneRecord.objects.filter(zone=zone).count()
        ZoneRecord.objects.filter(zone=zone).delete()
        self.log.records_deleted += deleted_count

        for parsed_rec in records:
            self._create_record(zone, parsed_rec)

    def _create_record(self, zone: HostedZone, parsed: ParsedRecord) -> None:
        self.log.records_seen += 1

        record = ZoneRecord(
            zone        = zone,
            name        = parsed.name,
            record_type = parsed.record_type,
            ttl         = parsed.ttl,
            values      = parsed.values,
            is_alias    = parsed.is_alias,
            alias_dns_name             = parsed.alias_dns_name,
            alias_hosted_zone_id       = parsed.alias_hosted_zone_id,
            alias_evaluate_target_health = parsed.alias_evaluate_target_health,
        )

        # Cross-reference to NetBox IPAddress (A and AAAA records only)
        if self.link_ips and not parsed.is_alias and parsed.values:
            if parsed.record_type in ("A", "AAAA"):
                record.linked_ip = self._find_ip(parsed.values[0])

        record.save()
        self.log.records_created += 1

    # ------------------------------------------------------------------
    # Domain → Zone linking
    # ------------------------------------------------------------------

    def _link_domains_to_zones(self, account: AWSAccount) -> None:
        """
        After all zones are committed, link each RegisteredDomain to the
        HostedZone whose apex name matches the domain name (with trailing dot).

        The match is case-insensitive.  Only zones belonging to the same
        account are considered.
        """
        zone_by_name: dict[str, HostedZone] = {
            z.name.lower().rstrip("."): z
            for z in HostedZone.objects.filter(account=account)
        }

        for domain in RegisteredDomain.objects.filter(account=account):
            key = domain.domain_name.lower().rstrip(".")
            matched_zone = zone_by_name.get(key)
            if matched_zone != domain.hosted_zone:
                domain.hosted_zone = matched_zone
                domain.save(update_fields=["hosted_zone"])

    # ------------------------------------------------------------------
    # IP cross-reference helper
    # ------------------------------------------------------------------

    @staticmethod
    def _find_ip(value: str):
        """
        Look up a plain IP address string in ipam.IPAddress.
        Returns the first matching IPAddress object or None.
        Only called when link_ip_addresses=True.
        """
        try:
            from ipam.models import IPAddress
            return (
                IPAddress.objects
                .filter(address__startswith=f"{value}/")
                .first()
            )
        except Exception as exc:
            log.debug("IP lookup failed for %r: %s", value, exc)
            return None
