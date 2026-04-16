from netbox.plugins import PluginConfig


class Route53SyncConfig(PluginConfig):
    name = "netbox_route53_sync"
    verbose_name = "Route53 Sync"
    description = "Import AWS Route53 hosted zones and records from multi-account JSON exports"
    version = "0.1.0"
    author = "NetBox Route53 Sync"
    base_url = "route53"
    min_version = "4.0.0"

    default_settings = {
        # Root directory that contains per-account sub-directories.
        # Directory layout is described in reader.py.
        # Can be overridden per-run with --data-root on the management command.
        "data_root": "/opt/route53-exports",

        # When True, records whose values resolve to a known NetBox IPAddress
        # will have a FK set to that object for cross-referencing.
        "link_ip_addresses": True,

        # When True, a SyncLog entry is created even for runs that found no
        # changes (useful for auditing scheduled jobs).
        "log_no_change_runs": True,
    }

    def ready(self):
        pass


config = Route53SyncConfig
