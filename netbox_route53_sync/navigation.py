from netbox.plugins.navigation import PluginMenu, PluginMenuButton, PluginMenuItem

menu = PluginMenu(
    label="Route53 Sync",
    groups=(
        (
            "DNS",
            (
                PluginMenuItem(
                    link="plugins:netbox_route53_sync:awsaccount_list",
                    link_text="AWS Accounts",
                ),
                PluginMenuItem(
                    link="plugins:netbox_route53_sync:hostedzone_list",
                    link_text="Hosted Zones",
                ),
                PluginMenuItem(
                    link="plugins:netbox_route53_sync:zonerecord_list",
                    link_text="Zone Records",
                ),
                PluginMenuItem(
                    link="plugins:netbox_route53_sync:registereddomain_list",
                    link_text="Registered Domains",
                ),
            ),
        ),
        (
            "Operations",
            (
                PluginMenuItem(
                    link="plugins:netbox_route53_sync:synclog_list",
                    link_text="Sync Logs",
                ),
            ),
        ),
    ),
    icon_class="mdi mdi-aws",
)
