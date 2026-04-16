import django.db.models.deletion
import taggit.managers
import utilities.json
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("extras", "0001_initial"),
        ("ipam", "0001_initial"),
        ("taggit", "0001_initial"),
        ("netbox_route53_sync", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ServiceLink",
            fields=[
                ("id",           models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created",      models.DateField(auto_now_add=True, null=True)),
                ("last_updated", models.DateTimeField(auto_now=True, null=True)),
                ("custom_field_data", models.JSONField(blank=True, default=dict, encoder=utilities.json.CustomFieldJSONEncoder)),
                (
                    "assigned_object_type",
                    models.ForeignKey(
                        limit_choices_to=models.Q(
                            app_label="netbox_route53_sync",
                            model__in=("awsaccount", "hostedzone", "registereddomain", "zonerecord"),
                        ),
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="contenttypes.contenttype",
                        verbose_name="Object Type",
                    ),
                ),
                ("assigned_object_id", models.PositiveBigIntegerField(verbose_name="Object ID")),
                (
                    "service",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="route53_links",
                        to="ipam.service",
                        verbose_name="Service",
                    ),
                ),
                (
                    "role",
                    models.CharField(
                        choices=[
                            ("technical-owner", "Technical Owner"),
                            ("business-owner",  "Business Owner"),
                            ("dns-provider",    "DNS Provider"),
                            ("serves",          "Serves"),
                            ("managed-by",      "Managed By"),
                            ("other",           "Other"),
                        ],
                        default="other",
                        max_length=30,
                        verbose_name="Role",
                    ),
                ),
                ("notes", models.TextField(blank=True, verbose_name="Notes")),
                ("tags", taggit.managers.TaggableManager(through="extras.TaggedItem", to="taggit.Tag")),
            ],
            options={
                "verbose_name":        "Service Link",
                "verbose_name_plural": "Service Links",
                "ordering": ["assigned_object_type", "assigned_object_id", "role"],
            },
        ),
        migrations.AddIndex(
            model_name="servicelink",
            index=models.Index(
                fields=["assigned_object_type", "assigned_object_id"],
                name="route53_servicelink_object_idx",
            ),
        ),
    ]
