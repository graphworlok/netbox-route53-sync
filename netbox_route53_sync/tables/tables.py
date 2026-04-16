import django_tables2 as tables
from netbox.tables import NetBoxTable, columns

from ..models import AWSAccount, HostedZone, RegisteredDomain, SyncLog, ZoneRecord


class AWSAccountTable(NetBoxTable):
    account_id     = tables.Column(linkify=True, verbose_name="Account ID")
    label          = tables.Column(verbose_name="Label")
    last_synced_at = tables.DateTimeColumn(verbose_name="Last Synced")
    zone_count = tables.Column(
        verbose_name="Zones",
        orderable=False,
    )
    domain_count = tables.Column(
        verbose_name="Domains",
        orderable=False,
    )
    actions = columns.ActionsColumn(actions=("edit", "delete"))

    class Meta(NetBoxTable.Meta):
        model = AWSAccount
        fields = ("pk", "account_id", "label", "zone_count", "domain_count", "last_synced_at", "actions")
        default_columns = ("account_id", "label", "zone_count", "domain_count", "last_synced_at", "actions")

    def render_zone_count(self, record):
        return record.hosted_zones.count()

    def render_domain_count(self, record):
        return record.registered_domains.count()


class HostedZoneTable(NetBoxTable):
    name       = tables.Column(linkify=True, verbose_name="Zone Name")
    zone_id    = tables.Column(verbose_name="Zone ID")
    account    = tables.Column(linkify=True, verbose_name="Account")
    zone_type  = columns.ChoiceFieldColumn(verbose_name="Type")
    record_count = tables.Column(verbose_name="Records")
    last_synced_at = tables.DateTimeColumn(verbose_name="Last Synced")
    actions = columns.ActionsColumn(actions=("edit", "delete"))

    class Meta(NetBoxTable.Meta):
        model = HostedZone
        fields = ("pk", "name", "zone_id", "account", "zone_type", "record_count", "last_synced_at", "actions")
        default_columns = ("name", "zone_id", "account", "zone_type", "record_count", "actions")


class ZoneRecordTable(NetBoxTable):
    name        = tables.Column(linkify=True, verbose_name="Name")
    record_type = columns.ChoiceFieldColumn(verbose_name="Type")
    ttl         = tables.Column(verbose_name="TTL")
    is_alias    = columns.BooleanColumn(verbose_name="Alias")
    zone        = tables.Column(linkify=True, verbose_name="Zone")
    actions = columns.ActionsColumn(actions=("delete",))

    class Meta(NetBoxTable.Meta):
        model = ZoneRecord
        fields = ("pk", "name", "record_type", "ttl", "is_alias", "zone", "actions")
        default_columns = ("name", "record_type", "ttl", "is_alias", "zone", "actions")


class RegisteredDomainTable(NetBoxTable):
    domain_name   = tables.Column(linkify=True, verbose_name="Domain Name")
    account       = tables.Column(linkify=True, verbose_name="Account")
    auto_renew    = columns.BooleanColumn(verbose_name="Auto Renew")
    transfer_lock = columns.BooleanColumn(verbose_name="Transfer Lock")
    expiry        = tables.DateTimeColumn(verbose_name="Expiry")
    hosted_zone   = tables.Column(linkify=True, verbose_name="Hosted Zone")
    actions = columns.ActionsColumn(actions=("delete",))

    class Meta(NetBoxTable.Meta):
        model = RegisteredDomain
        fields = ("pk", "domain_name", "account", "auto_renew", "transfer_lock", "expiry", "hosted_zone", "actions")
        default_columns = ("domain_name", "account", "expiry", "auto_renew", "hosted_zone", "actions")


class SyncLogTable(NetBoxTable):
    account_id    = tables.Column(verbose_name="Account ID", linkify=True)
    account_label = tables.Column(verbose_name="Account Label")
    status        = columns.ChoiceFieldColumn(verbose_name="Status")
    started_at    = tables.DateTimeColumn(verbose_name="Started")
    completed_at  = tables.DateTimeColumn(verbose_name="Completed")
    domains_seen  = tables.Column(verbose_name="Domains")
    zones_seen    = tables.Column(verbose_name="Zones")
    records_seen  = tables.Column(verbose_name="Records")

    class Meta(NetBoxTable.Meta):
        model = SyncLog
        fields = (
            "pk", "account_id", "account_label", "status",
            "started_at", "completed_at",
            "domains_seen", "zones_seen", "records_seen",
        )
        default_columns = (
            "account_id", "account_label", "status",
            "started_at", "zones_seen", "records_seen",
        )
