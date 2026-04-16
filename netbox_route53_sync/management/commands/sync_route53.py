"""
Management command: sync_route53

Reads AWS Route53 JSON export files and syncs them into NetBox.

Data root layout expected:

    <data_root>/
      AWS/
        <account_id>/
            Registered_Domains.json     (aws route53domains list-domains)
            hostedzone/
                <zone_id>.json          (aws route53 list-resource-record-sets)

Usage
-----
  # Sync all accounts found under the configured data_root
  python manage.py sync_route53

  # Override the data directory for this run
  python manage.py sync_route53 --data-root /mnt/s3/route53-exports

  # Sync a single AWS account only
  python manage.py sync_route53 --account 123456789012

  # Dry run — parse files and report counts without writing to the database
  python manage.py sync_route53 --dry-run

  # Also link A/AAAA record values to matching NetBox IPAddress objects
  python manage.py sync_route53 --link-ips

  # List all account directories found under data_root and exit
  python manage.py sync_route53 --list-accounts

Configuration
-------------
Set data_root in NetBox's PLUGINS_CONFIG:

    PLUGINS_CONFIG = {
        "netbox_route53_sync": {
            "data_root":        "/opt/route53-exports",
            "link_ip_addresses": True,
        }
    }

Scheduling
----------
    # /etc/cron.d/netbox-route53-sync
    0 2 * * * netbox /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py \\
        sync_route53 >> /var/log/netbox/route53_sync.log 2>&1
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.base import BaseCommand

from ...choices import SyncStatusChoices
from ...models import SyncLog
from ...reader import ParsedAccount, read_account, read_all_accounts
from ...syncer import Route53Syncer

logger = logging.getLogger(__name__)


def _plugin_setting(key: str, default=None):
    try:
        from netbox.plugins import get_plugin_config
        return get_plugin_config("netbox_route53_sync", key) or default
    except Exception:
        return default


class Command(BaseCommand):
    help = "Sync AWS Route53 hosted zones and registered domains from JSON export files."

    def add_arguments(self, parser):
        parser.add_argument(
            "--data-root",
            metavar="PATH",
            default=None,
            help=(
                "Root directory containing the AWS/<account_id>/ folder tree. "
                "Overrides the data_root plugin setting for this run."
            ),
        )
        parser.add_argument(
            "--account",
            metavar="ACCOUNT_ID",
            default=None,
            help=(
                "Sync only this AWS account ID (12-digit number). "
                "Default: sync all account directories found under data_root."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse files and report counts but write nothing to the database.",
        )
        parser.add_argument(
            "--link-ips",
            action="store_true",
            default=None,
            help=(
                "Cross-reference A/AAAA record values to matching NetBox "
                "IPAddress objects.  Overrides the link_ip_addresses plugin setting."
            ),
        )
        parser.add_argument(
            "--list-accounts",
            action="store_true",
            help=(
                "List all account directories found under data_root and exit. "
                "Useful for discovering available account IDs."
            ),
        )

    def handle(self, *args, **options):
        data_root = (
            options.get("data_root")
            or _plugin_setting("data_root", "/opt/route53-exports")
        )
        dry_run     = options["dry_run"]
        account_filter = options.get("account")
        list_accounts  = options.get("list_accounts")

        # Resolve link_ips: CLI flag > plugin setting
        link_ips_flag = options.get("link_ips")
        link_ips = (
            link_ips_flag
            if link_ips_flag is not None
            else bool(_plugin_setting("link_ip_addresses", True))
        )

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no database writes"))

        # ------------------------------------------------------------------
        # Validate data root
        # ------------------------------------------------------------------
        aws_root = Path(data_root) / "AWS"
        if not aws_root.is_dir():
            self.stderr.write(self.style.ERROR(
                f"Data directory not found: {aws_root}\n"
                f"Expected layout: {data_root}/AWS/<account_id>/"
            ))
            sys.exit(1)

        # ------------------------------------------------------------------
        # --list-accounts mode
        # ------------------------------------------------------------------
        if list_accounts:
            self._list_accounts(aws_root)
            return

        # ------------------------------------------------------------------
        # Read files
        # ------------------------------------------------------------------
        try:
            if account_filter:
                parsed_accounts = [read_account(data_root, account_filter)]
            else:
                parsed_accounts = read_all_accounts(data_root)
        except FileNotFoundError as exc:
            self.stderr.write(self.style.ERROR(str(exc)))
            sys.exit(1)

        if not parsed_accounts:
            self.stdout.write(self.style.WARNING(
                f"No account directories found under {aws_root}.\n"
                "Expected 12-digit numeric folder names."
            ))
            return

        self.stdout.write(
            f"Found {len(parsed_accounts)} account(s).  "
            f"Syncing into NetBox…"
        )

        # ------------------------------------------------------------------
        # Sync each account
        # ------------------------------------------------------------------
        total_accounts   = 0
        failed_accounts  = 0

        for parsed in parsed_accounts:
            self.stdout.write(
                f"\n[Account {parsed.account_id}]"
                + (f"  {len(parsed.errors)} read error(s)" if parsed.errors else "")
            )
            for err in parsed.errors:
                self.stdout.write(self.style.WARNING(f"  ! {err}"))

            sync_log = SyncLog(
                account_id    = parsed.account_id,
                account_label = "",
                status        = SyncStatusChoices.RUNNING,
            )

            syncer = Route53Syncer(
                sync_log = sync_log,
                dry_run  = dry_run,
                link_ips = link_ips,
            )

            try:
                syncer.sync(parsed)
                errors = bool(parsed.errors)
                syncer.close(
                    success = True,
                    message = "; ".join(parsed.errors) if errors else "",
                )

                self.stdout.write(self.style.SUCCESS(
                    f"  Domains : {sync_log.domains_seen} seen, "
                    f"{sync_log.domains_created} created, "
                    f"{sync_log.domains_updated} updated\n"
                    f"  Zones   : {sync_log.zones_seen} seen, "
                    f"{sync_log.zones_created} created, "
                    f"{sync_log.zones_updated} updated\n"
                    f"  Records : {sync_log.records_seen} imported, "
                    f"{sync_log.records_deleted} replaced"
                ))
                total_accounts += 1

            except Exception as exc:
                logger.exception(
                    "Sync failed for account %s", parsed.account_id
                )
                syncer.close(success=False, message=str(exc))
                self.stderr.write(self.style.ERROR(
                    f"  FAILED: {exc}"
                ))
                failed_accounts += 1

        # ------------------------------------------------------------------
        # Summary
        # ------------------------------------------------------------------
        self.stdout.write("")
        if dry_run:
            self.stdout.write(self.style.WARNING(
                f"Dry-run complete — {total_accounts} account(s) parsed, "
                f"{failed_accounts} failed."
            ))
        else:
            style = self.style.SUCCESS if not failed_accounts else self.style.WARNING
            self.stdout.write(style(
                f"Sync complete — {total_accounts} account(s) synced"
                + (f", {failed_accounts} failed" if failed_accounts else "")
            ))

    # ------------------------------------------------------------------

    def _list_accounts(self, aws_root: Path) -> None:
        import re
        self.stdout.write(f"Account directories under {aws_root}:\n")
        found = False
        for entry in sorted(aws_root.iterdir()):
            if not entry.is_dir():
                continue
            is_account = bool(re.fullmatch(r"\d{12}", entry.name))
            hz_count   = len(list((entry / "hostedzone").glob("*.json"))) if (entry / "hostedzone").is_dir() else 0
            has_domains = (entry / "Registered_Domains.json").is_file()
            marker = "" if is_account else "  [not a valid 12-digit account ID]"
            self.stdout.write(
                f"  {entry.name}{marker}\n"
                f"    Registered_Domains.json : {'yes' if has_domains else 'no'}\n"
                f"    hostedzone/*.json       : {hz_count} file(s)"
            )
            found = True
        if not found:
            self.stdout.write(self.style.WARNING("  (none found)"))
