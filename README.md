# netbox-route53-sync

A NetBox 4.x plugin that imports AWS Route53 hosted zones, zone records, and registered domains from JSON files exported from multiple AWS accounts.

No live AWS API calls are made at sync time — the plugin reads files that have already been exported and placed in a structured directory tree.

---

## What gets imported

| NetBox object | Source |
|---|---|
| `AWSAccount` | One per `AWS/<account_id>/` directory |
| `HostedZone` | One per `hostedzone/<zone_id>.json` file |
| `ZoneRecord` | Every `ResourceRecordSet` entry in each zone file |
| `RegisteredDomain` | Every entry in `Registered_Domains.json` |

Registered domains are automatically linked to their hosted zone by matching the domain name against zone apex names after both are imported.

A/AAAA record values are optionally cross-referenced to matching `ipam.IPAddress` records in NetBox (no IPs are created — read-only lookup only).

---

## Data directory layout

```
<data_root>/
  AWS/
    <account_id>/                       12-digit numeric AWS account ID
        Registered_Domains.json         aws route53domains list-domains
        hostedzone/
            <zone_id>.json              aws route53 list-resource-record-sets
            <zone_id>.json
            …
    <account_id>/
        …
```

### Exporting from AWS

```bash
# Export registered domains for an account
aws route53domains list-domains \
    --region us-east-1 \
    > AWS/123456789012/Registered_Domains.json

# Export all record sets for a hosted zone
ZONE_ID=Z1D633PJN98FT9
aws route53 list-resource-record-sets \
    --hosted-zone-id "$ZONE_ID" \
    > AWS/123456789012/hostedzone/${ZONE_ID}.json
```

To export all zones for an account in one script:

```bash
ACCOUNT_ID=123456789012
mkdir -p AWS/${ACCOUNT_ID}/hostedzone

# Registered domains
aws route53domains list-domains --region us-east-1 \
    > AWS/${ACCOUNT_ID}/Registered_Domains.json

# All hosted zones
for ZONE_ID in $(aws route53 list-hosted-zones \
    --query 'HostedZones[].Id' --output text | tr '\t' '\n' | sed 's|/hostedzone/||'); do
    aws route53 list-resource-record-sets --hosted-zone-id "$ZONE_ID" \
        > AWS/${ACCOUNT_ID}/hostedzone/${ZONE_ID}.json
done
```

---

## Requirements

- NetBox 4.0 or later
- Python 3.10+
- No additional Python packages required (standard library only for file reading)

---

## Installation

### 1. Install the package

```bash
source /opt/netbox/venv/bin/activate
pip install netbox-route53-sync

# Or from a local clone
pip install /path/to/netbox-route53-sync
```

### 2. Enable the plugin

Edit NetBox's `configuration.py`:

```python
PLUGINS = [
    "netbox_route53_sync",
]
```

### 3. Configure the plugin

```python
PLUGINS_CONFIG = {
    "netbox_route53_sync": {
        # Root directory containing the AWS/<account_id>/ folder tree.
        "data_root": "/opt/route53-exports",

        # When True, A/AAAA record values are cross-referenced to NetBox
        # IPAddress objects.  No IPs are created — read-only lookup only.
        "link_ip_addresses": True,

        # When True, a SyncLog entry is written even when no changes are found.
        "log_no_change_runs": True,
    }
}
```

### 4. Run migrations

```bash
source /opt/netbox/venv/bin/activate
cd /opt/netbox/netbox
python manage.py migrate netbox_route53_sync
```

### 5. Restart NetBox

```bash
sudo systemctl restart netbox netbox-rq
```

The plugin appears under **Plugins → Route53 Sync** in the navigation menu.

---

## Running a sync

```bash
# Sync all accounts found under data_root
python manage.py sync_route53

# Override data directory for this run
python manage.py sync_route53 --data-root /mnt/s3/exports

# Sync a single account only
python manage.py sync_route53 --account 123456789012

# Dry run — parse files and print counts without writing to the database
python manage.py sync_route53 --dry-run

# Also cross-reference A/AAAA values to NetBox IP addresses
python manage.py sync_route53 --link-ips

# List all account directories found under data_root
python manage.py sync_route53 --list-accounts
```

### Scheduling

```
# /etc/cron.d/netbox-route53-sync

# Sync every night after the export script runs
30 2 * * * netbox /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py \
    sync_route53 >> /var/log/netbox/route53_sync.log 2>&1
```

---

## JSON formats handled

### `Registered_Domains.json`

Output of `aws route53domains list-domains`:

```json
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
```

### `hostedzone/<zone_id>.json`

Output of `aws route53 list-resource-record-sets --hosted-zone-id <id>`:

```json
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
```

The zone apex name (e.g. `example.com.`) is inferred from the `Name` field of the first SOA or NS record — it is not encoded in the filename.

If `IsTruncated` is `true` a warning is logged and the available records are still imported. Re-export the zone with `--max-items` removed to get a complete file.

---

## Data model notes

- **Zone records are fully replaced** on each sync. Route53 is the authoritative source; manual edits to `ZoneRecord` rows will be overwritten on the next run.
- **Registered domains** and **Hosted zones** are upserted — existing records are updated, not recreated.
- **Zone type** (public/private) is not available from `list-resource-record-sets`. It defaults to `Public` and can be corrected manually in the NetBox UI.
- **Zone name** is inferred from the SOA/NS apex record. If neither is present (unusual), the zone ID is used as the name.

---

## REST API

All objects are accessible read-only under `/api/plugins/route53/`:

```
GET /api/plugins/route53/accounts/
GET /api/plugins/route53/hosted-zones/
GET /api/plugins/route53/zone-records/?zone_id=Z1D633PJN98FT9
GET /api/plugins/route53/zone-records/?type=A
GET /api/plugins/route53/registered-domains/
GET /api/plugins/route53/sync-logs/
```

---

## Project structure

```
netbox-route53-sync/
├── netbox_route53_sync/
│   ├── __init__.py             PluginConfig (base_url="route53")
│   ├── choices.py              SyncStatusChoices, ZoneTypeChoices, RecordTypeChoices
│   ├── reader.py               JSON file parser — no ORM, returns ParsedAccount objects
│   ├── syncer.py               Django ORM writer — upserts all objects
│   ├── filtersets.py
│   ├── models/
│   │   ├── aws_account.py      AWSAccount
│   │   ├── hosted_zone.py      HostedZone
│   │   ├── zone_record.py      ZoneRecord
│   │   ├── registered_domain.py RegisteredDomain
│   │   └── sync_log.py         SyncLog (plain model, write-once)
│   ├── management/commands/
│   │   └── sync_route53.py     CLI: --account, --data-root, --dry-run, --link-ips, --list-accounts
│   ├── tables/
│   ├── forms/
│   ├── filtersets.py
│   ├── views/
│   ├── api/
│   ├── navigation.py
│   ├── urls.py
│   ├── migrations/
│   │   └── 0001_initial.py
│   └── templates/
│       └── netbox_route53_sync/
│           ├── awsaccount.html
│           ├── hostedzone.html
│           ├── zonerecord.html
│           ├── registereddomain.html
│           └── synclog.html
└── pyproject.toml
```
