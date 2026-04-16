"""
Route53 JSON file reader.

Walks the data root directory and parses every account's exported JSON files
into plain Python dataclasses.  No Django ORM calls are made here — the syncer
handles all database writes.

Expected directory layout
--------------------------
    <data_root>/
      AWS/
        <account_id>/                   ← numeric AWS account ID (folder name)
            Registered_Domains.json     ← aws route53domains list-domains
            hostedzone/
                <zone_id>.json          ← aws route53 list-resource-record-sets

File formats
------------

Registered_Domains.json
  Output of:  aws route53domains list-domains > Registered_Domains.json

  {
      "Domains": [
          {
              "DomainName":   "example.com",
              "AutoRenew":    true,
              "TransferLock": true,
              "Expiry":       "2027-03-15T00:00:00+00:00"
          }
      ],
      "NextPageMarker": "..."   <- present only when paginated; ignored here
                                   (the file is assumed to be a complete export)
  }

hostedzone/<zone_id>.json
  Output of:  aws route53 list-resource-record-sets --hosted-zone-id $ZONEID

  {
      "ResourceRecordSets": [
          {
              "Name": "example.com.",
              "Type": "SOA",
              "TTL":  900,
              "ResourceRecords": [{"Value": "ns-1.awsdns-1.org. ..."}]
          },
          {
              "Name": "www.example.com.",
              "Type": "A",
              "TTL":  300,
              "ResourceRecords": [{"Value": "1.2.3.4"}]
          },
          {
              "Name": "cdn.example.com.",
              "Type": "A",
              "AliasTarget": {
                  "HostedZoneId":         "Z2FDTNDATAQYW2",
                  "DNSName":              "d111111abcdef8.cloudfront.net.",
                  "EvaluateTargetHealth": false
              }
          }
      ],
      "IsTruncated": false,
      "MaxItems":    "300"
  }

  Note: IsTruncated will be false for complete exports.  If it is true the
  file is incomplete and a warning is logged; the available records are still
  imported.

Zone name inference
-------------------
The filename is the AWS zone ID (not the domain name).  The zone apex name is
inferred from the first SOA or NS record found in ResourceRecordSets — AWS
always returns these at the top of the list.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

# File and folder names (exact, case-sensitive)
_AWS_FOLDER            = "AWS"
_DOMAINS_FILE          = "Registered_Domains.json"
_HOSTEDZONE_FOLDER     = "hostedzone"

# JSON keys — aws route53domains list-domains
_KEY_DOMAINS           = "Domains"
_KEY_DOMAIN_NAME       = "DomainName"
_KEY_AUTO_RENEW        = "AutoRenew"
_KEY_TRANSFER_LOCK     = "TransferLock"
_KEY_EXPIRY            = "Expiry"

# JSON keys — aws route53 list-resource-record-sets
_KEY_RECORD_SETS       = "ResourceRecordSets"
_KEY_IS_TRUNCATED      = "IsTruncated"
_KEY_RRS_NAME          = "Name"
_KEY_RRS_TYPE          = "Type"
_KEY_RRS_TTL           = "TTL"
_KEY_RRS_RECORDS       = "ResourceRecords"
_KEY_RRS_RECORD_VALUE  = "Value"
_KEY_ALIAS_TARGET      = "AliasTarget"
_KEY_ALIAS_ZONE_ID     = "HostedZoneId"
_KEY_ALIAS_DNS_NAME    = "DNSName"
_KEY_ALIAS_EVAL_HEALTH = "EvaluateTargetHealth"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ParsedDomain:
    domain_name:   str
    auto_renew:    bool = True
    transfer_lock: bool = True
    expiry:        Optional[datetime] = None


@dataclass
class ParsedRecord:
    name:        str
    record_type: str
    ttl:         Optional[int]
    values:      list[str]         = field(default_factory=list)
    is_alias:    bool              = False
    alias_dns_name:          str   = ""
    alias_hosted_zone_id:    str   = ""
    alias_evaluate_target_health: Optional[bool] = None


@dataclass
class ParsedZone:
    zone_id:  str
    name:     str              # apex name with trailing dot, e.g. "example.com."
    records:  list[ParsedRecord] = field(default_factory=list)
    truncated: bool = False    # True if the source file had IsTruncated=true


@dataclass
class ParsedAccount:
    account_id: str
    domains:    list[ParsedDomain] = field(default_factory=list)
    zones:      list[ParsedZone]   = field(default_factory=list)
    errors:     list[str]          = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def read_all_accounts(data_root: str | Path) -> list[ParsedAccount]:
    """
    Walk <data_root>/AWS/ and parse every account sub-directory.

    Returns a list of ParsedAccount objects (one per account folder found).
    Errors reading individual files are recorded on the ParsedAccount rather
    than raising, so a bad file in one account does not abort the others.
    """
    root = Path(data_root) / _AWS_FOLDER
    if not root.is_dir():
        raise FileNotFoundError(
            f"AWS data directory not found: {root}\n"
            f"Expected layout: {data_root}/{_AWS_FOLDER}/<account_id>/"
        )

    accounts: list[ParsedAccount] = []

    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        if not re.fullmatch(r"\d{12}", entry.name):
            log.debug(
                "Skipping non-account-ID directory: %s (expected 12-digit number)",
                entry.name,
            )
            continue
        accounts.append(_read_account(entry))

    if not accounts:
        log.warning(
            "No AWS account directories found under %s. "
            "Expected 12-digit numeric folder names.",
            root,
        )

    return accounts


def read_account(data_root: str | Path, account_id: str) -> ParsedAccount:
    """Read a single account directory."""
    account_dir = Path(data_root) / _AWS_FOLDER / account_id
    if not account_dir.is_dir():
        raise FileNotFoundError(f"Account directory not found: {account_dir}")
    return _read_account(account_dir)


# ---------------------------------------------------------------------------
# Per-account parsing
# ---------------------------------------------------------------------------

def _read_account(account_dir: Path) -> ParsedAccount:
    account_id = account_dir.name
    log.info("Reading account %s from %s", account_id, account_dir)

    account = ParsedAccount(account_id=account_id)

    # --- Registered domains ---
    domains_file = account_dir / _DOMAINS_FILE
    if domains_file.is_file():
        try:
            account.domains = _parse_domains_file(domains_file)
            log.info(
                "Account %s: %d registered domain(s)", account_id, len(account.domains)
            )
        except Exception as exc:
            msg = f"Failed to parse {domains_file}: {exc}"
            log.warning(msg)
            account.errors.append(msg)
    else:
        log.info("Account %s: no %s found", account_id, _DOMAINS_FILE)

    # --- Hosted zones ---
    hz_dir = account_dir / _HOSTEDZONE_FOLDER
    if hz_dir.is_dir():
        for zone_file in sorted(hz_dir.glob("*.json")):
            try:
                zone = _parse_zone_file(zone_file)
                account.zones.append(zone)
                log.info(
                    "Account %s: zone %s (%s) — %d record(s)%s",
                    account_id,
                    zone.zone_id,
                    zone.name,
                    len(zone.records),
                    " [TRUNCATED]" if zone.truncated else "",
                )
            except Exception as exc:
                msg = f"Failed to parse {zone_file}: {exc}"
                log.warning(msg)
                account.errors.append(msg)
    else:
        log.info("Account %s: no %s/ directory found", account_id, _HOSTEDZONE_FOLDER)

    return account


# ---------------------------------------------------------------------------
# Registered_Domains.json parser
# ---------------------------------------------------------------------------

def _parse_domains_file(path: Path) -> list[ParsedDomain]:
    """
    Parse Registered_Domains.json.

    Expected structure (aws route53domains list-domains):
    {
        "Domains": [
            {
                "DomainName":   "example.com",
                "AutoRenew":    true,
                "TransferLock": true,
                "Expiry":       "2027-03-15T00:00:00+00:00"
            }
        ]
    }
    """
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)

    raw_domains = data.get(_KEY_DOMAINS, [])
    if not isinstance(raw_domains, list):
        raise ValueError(f"Expected '{_KEY_DOMAINS}' to be a list in {path}")

    domains: list[ParsedDomain] = []
    for raw in raw_domains:
        name = raw.get(_KEY_DOMAIN_NAME, "").strip()
        if not name:
            log.warning("Skipping domain entry with no %s in %s", _KEY_DOMAIN_NAME, path)
            continue

        domains.append(ParsedDomain(
            domain_name   = name,
            auto_renew    = bool(raw.get(_KEY_AUTO_RENEW, True)),
            transfer_lock = bool(raw.get(_KEY_TRANSFER_LOCK, True)),
            expiry        = _parse_datetime(raw.get(_KEY_EXPIRY)),
        ))

    return domains


# ---------------------------------------------------------------------------
# hostedzone/<zone_id>.json parser
# ---------------------------------------------------------------------------

def _parse_zone_file(path: Path) -> ParsedZone:
    """
    Parse one hosted zone record-sets file.

    Expected structure (aws route53 list-resource-record-sets):
    {
        "ResourceRecordSets": [
            {
                "Name": "example.com.",
                "Type": "SOA",
                "TTL":  900,
                "ResourceRecords": [{"Value": "..."}]
            },
            {
                "Name": "www.example.com.",
                "Type": "A",
                "TTL":  300,
                "ResourceRecords": [{"Value": "1.2.3.4"}]
            },
            {
                "Name": "cdn.example.com.",
                "Type": "A",
                "AliasTarget": {
                    "HostedZoneId":         "Z2FDTNDATAQYW2",
                    "DNSName":              "d111111abcdef8.cloudfront.net.",
                    "EvaluateTargetHealth": false
                }
            }
        ],
        "IsTruncated": false,
        "MaxItems": "300"
    }
    """
    # Zone ID is the filename without extension.
    # Strip any leading path components (e.g. if someone saved as /hostedzone/ZXXX)
    zone_id = path.stem.split("/")[-1].split("\\")[-1]

    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)

    raw_sets = data.get(_KEY_RECORD_SETS, [])
    if not isinstance(raw_sets, list):
        raise ValueError(
            f"Expected '{_KEY_RECORD_SETS}' to be a list in {path}"
        )

    truncated = bool(data.get(_KEY_IS_TRUNCATED, False))
    if truncated:
        log.warning(
            "Zone file %s has IsTruncated=true — the export is incomplete. "
            "Records available will still be imported.",
            path,
        )

    records: list[ParsedRecord] = []
    for raw in raw_sets:
        record = _parse_record_set(raw, path)
        if record:
            records.append(record)

    # Infer zone name from the first SOA or NS record at the apex
    zone_name = _infer_zone_name(records, zone_id, path)

    return ParsedZone(
        zone_id   = zone_id,
        name      = zone_name,
        records   = records,
        truncated = truncated,
    )


def _parse_record_set(raw: dict, source_path: Path) -> Optional[ParsedRecord]:
    """Parse one ResourceRecordSet entry."""
    name = raw.get(_KEY_RRS_NAME, "").strip()
    rtype = raw.get(_KEY_RRS_TYPE, "").strip().upper()

    if not name or not rtype:
        log.debug("Skipping record with missing Name or Type in %s: %s", source_path, raw)
        return None

    # Ensure trailing dot (AWS always includes it, but be defensive)
    if not name.endswith("."):
        name = name + "."

    ttl = raw.get(_KEY_RRS_TTL)
    if ttl is not None:
        try:
            ttl = int(ttl)
        except (TypeError, ValueError):
            ttl = None

    alias_target = raw.get(_KEY_ALIAS_TARGET)

    if alias_target:
        # Alias record — no ResourceRecords, no TTL
        return ParsedRecord(
            name        = name,
            record_type = rtype,
            ttl         = None,
            values      = [],
            is_alias    = True,
            alias_dns_name          = alias_target.get(_KEY_ALIAS_DNS_NAME, "").strip(),
            alias_hosted_zone_id    = alias_target.get(_KEY_ALIAS_ZONE_ID, "").strip(),
            alias_evaluate_target_health = alias_target.get(_KEY_ALIAS_EVAL_HEALTH),
        )
    else:
        # Standard record
        raw_records = raw.get(_KEY_RRS_RECORDS, [])
        values = [
            r.get(_KEY_RRS_RECORD_VALUE, "")
            for r in raw_records
            if r.get(_KEY_RRS_RECORD_VALUE)
        ]
        return ParsedRecord(
            name        = name,
            record_type = rtype,
            ttl         = ttl,
            values      = values,
        )


def _infer_zone_name(
    records: list[ParsedRecord],
    zone_id: str,
    source_path: Path,
) -> str:
    """
    Infer the zone apex name from the first SOA or NS record in the record set.

    AWS always returns SOA and NS records for the zone apex at the top of
    list-resource-record-sets output.  The Name field of these records is the
    zone apex with a trailing dot.

    Falls back to the zone_id if no SOA/NS record is found (e.g. an empty or
    malformed file).
    """
    for priority_type in ("SOA", "NS"):
        for record in records:
            if record.record_type == priority_type:
                log.debug(
                    "Zone %s: apex name inferred from %s record: %s",
                    zone_id, priority_type, record.name,
                )
                return record.name

    log.warning(
        "Could not infer zone name for %s (no SOA or NS record found). "
        "Using zone ID as fallback name.",
        source_path,
    )
    return f"{zone_id}."


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_datetime(value) -> Optional[datetime]:
    """Parse an ISO 8601 datetime string from AWS output, returning UTC-aware datetime."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError) as exc:
        log.debug("Could not parse datetime %r: %s", value, exc)
        return None
