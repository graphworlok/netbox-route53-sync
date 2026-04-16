import django.db.models.deletion
import taggit.managers
import utilities.json
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("extras", "0001_initial"),
        ("ipam", "0001_initial"),
        ("taggit", "0001_initial"),
    ]

    operations = [
        # ----------------------------------------------------------------
        # AWSAccount
        # ----------------------------------------------------------------
        migrations.CreateModel(
            name="AWSAccount",
            fields=[
                ("id",           models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created",      models.DateField(auto_now_add=True, null=True)),
                ("last_updated", models.DateTimeField(auto_now=True, null=True)),
                ("custom_field_data", models.JSONField(blank=True, default=dict, encoder=utilities.json.CustomFieldJSONEncoder)),
                ("account_id",   models.CharField(db_index=True, max_length=20, unique=True, verbose_name="Account ID")),
                ("label",        models.CharField(blank=True, max_length=200, verbose_name="Label")),
                ("last_synced_at", models.DateTimeField(blank=True, null=True, verbose_name="Last Synced")),
                ("tags", taggit.managers.TaggableManager(through="extras.TaggedItem", to="taggit.Tag")),
            ],
            options={
                "verbose_name":        "AWS Account",
                "verbose_name_plural": "AWS Accounts",
                "ordering": ["account_id"],
            },
        ),

        # ----------------------------------------------------------------
        # HostedZone
        # ----------------------------------------------------------------
        migrations.CreateModel(
            name="HostedZone",
            fields=[
                ("id",           models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created",      models.DateField(auto_now_add=True, null=True)),
                ("last_updated", models.DateTimeField(auto_now=True, null=True)),
                ("custom_field_data", models.JSONField(blank=True, default=dict, encoder=utilities.json.CustomFieldJSONEncoder)),
                ("account",      models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="hosted_zones", to="netbox_route53_sync.awsaccount", verbose_name="AWS Account")),
                ("zone_id",      models.CharField(db_index=True, max_length=64, unique=True, verbose_name="Zone ID")),
                ("name",         models.CharField(db_index=True, max_length=253, verbose_name="Zone Name")),
                ("zone_type",    models.CharField(choices=[("public", "Public"), ("private", "Private")], default="public", max_length=10, verbose_name="Type")),
                ("record_count", models.PositiveIntegerField(default=0, verbose_name="Record Count")),
                ("comment",      models.TextField(blank=True, verbose_name="Comment")),
                ("last_synced_at", models.DateTimeField(blank=True, null=True, verbose_name="Last Synced")),
                ("tags", taggit.managers.TaggableManager(through="extras.TaggedItem", to="taggit.Tag")),
            ],
            options={
                "verbose_name":        "Hosted Zone",
                "verbose_name_plural": "Hosted Zones",
                "ordering": ["name", "zone_id"],
            },
        ),
        migrations.AddConstraint(
            model_name="hostedzone",
            constraint=models.UniqueConstraint(fields=("account", "zone_id"), name="unique_account_zone"),
        ),

        # ----------------------------------------------------------------
        # ZoneRecord
        # ----------------------------------------------------------------
        migrations.CreateModel(
            name="ZoneRecord",
            fields=[
                ("id",           models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created",      models.DateField(auto_now_add=True, null=True)),
                ("last_updated", models.DateTimeField(auto_now=True, null=True)),
                ("custom_field_data", models.JSONField(blank=True, default=dict, encoder=utilities.json.CustomFieldJSONEncoder)),
                ("zone",         models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="records", to="netbox_route53_sync.hostedzone", verbose_name="Hosted Zone")),
                ("name",         models.CharField(db_index=True, max_length=253, verbose_name="Name")),
                ("record_type",  models.CharField(db_index=True, max_length=10, verbose_name="Type")),
                ("ttl",          models.PositiveIntegerField(blank=True, null=True, verbose_name="TTL")),
                ("values",       models.JSONField(blank=True, default=list, verbose_name="Values")),
                ("is_alias",     models.BooleanField(db_index=True, default=False, verbose_name="Alias")),
                ("alias_dns_name",       models.CharField(blank=True, max_length=253, verbose_name="Alias DNS Name")),
                ("alias_hosted_zone_id", models.CharField(blank=True, max_length=64, verbose_name="Alias Hosted Zone ID")),
                ("alias_evaluate_target_health", models.BooleanField(blank=True, null=True, verbose_name="Evaluate Target Health")),
                ("linked_ip",    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="route53_records", to="ipam.ipaddress", verbose_name="Linked IP")),
                ("tags", taggit.managers.TaggableManager(through="extras.TaggedItem", to="taggit.Tag")),
            ],
            options={
                "verbose_name":        "Zone Record",
                "verbose_name_plural": "Zone Records",
                "ordering": ["zone", "name", "record_type"],
            },
        ),

        # ----------------------------------------------------------------
        # RegisteredDomain
        # ----------------------------------------------------------------
        migrations.CreateModel(
            name="RegisteredDomain",
            fields=[
                ("id",           models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created",      models.DateField(auto_now_add=True, null=True)),
                ("last_updated", models.DateTimeField(auto_now=True, null=True)),
                ("custom_field_data", models.JSONField(blank=True, default=dict, encoder=utilities.json.CustomFieldJSONEncoder)),
                ("account",      models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="registered_domains", to="netbox_route53_sync.awsaccount", verbose_name="AWS Account")),
                ("domain_name",  models.CharField(db_index=True, max_length=253, verbose_name="Domain Name")),
                ("auto_renew",   models.BooleanField(default=True, verbose_name="Auto Renew")),
                ("transfer_lock", models.BooleanField(default=True, verbose_name="Transfer Lock")),
                ("expiry",       models.DateTimeField(blank=True, null=True, verbose_name="Expiry")),
                ("hosted_zone",  models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="registered_domains", to="netbox_route53_sync.hostedzone", verbose_name="Hosted Zone")),
                ("last_synced_at", models.DateTimeField(blank=True, null=True, verbose_name="Last Synced")),
                ("tags", taggit.managers.TaggableManager(through="extras.TaggedItem", to="taggit.Tag")),
            ],
            options={
                "verbose_name":        "Registered Domain",
                "verbose_name_plural": "Registered Domains",
                "ordering": ["domain_name"],
            },
        ),
        migrations.AddConstraint(
            model_name="registereddomain",
            constraint=models.UniqueConstraint(fields=("account", "domain_name"), name="unique_account_domain"),
        ),

        # ----------------------------------------------------------------
        # SyncLog (plain model — no NetBoxModel base)
        # ----------------------------------------------------------------
        migrations.CreateModel(
            name="SyncLog",
            fields=[
                ("id",           models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("account_id",   models.CharField(db_index=True, max_length=20)),
                ("account_label", models.CharField(blank=True, max_length=200)),
                ("started_at",   models.DateTimeField(auto_now_add=True, db_index=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("status",       models.CharField(
                    choices=[
                        ("pending", "Pending"), ("running", "Running"),
                        ("success", "Success"), ("partial", "Partial"), ("failed", "Failed"),
                    ],
                    db_index=True, default="pending", max_length=20,
                )),
                ("message",          models.TextField(blank=True)),
                ("domains_seen",     models.PositiveIntegerField(default=0)),
                ("domains_created",  models.PositiveIntegerField(default=0)),
                ("domains_updated",  models.PositiveIntegerField(default=0)),
                ("zones_seen",       models.PositiveIntegerField(default=0)),
                ("zones_created",    models.PositiveIntegerField(default=0)),
                ("zones_updated",    models.PositiveIntegerField(default=0)),
                ("records_seen",     models.PositiveIntegerField(default=0)),
                ("records_created",  models.PositiveIntegerField(default=0)),
                ("records_updated",  models.PositiveIntegerField(default=0)),
                ("records_deleted",  models.PositiveIntegerField(default=0)),
            ],
            options={
                "verbose_name":        "Sync Log",
                "verbose_name_plural": "Sync Logs",
                "ordering": ["-started_at"],
            },
        ),
    ]
