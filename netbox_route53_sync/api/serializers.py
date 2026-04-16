from rest_framework import serializers

from ..models import AWSAccount, HostedZone, RegisteredDomain, ServiceLink, SyncLog, ZoneRecord


class AWSAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model  = AWSAccount
        fields = ["id", "account_id", "label", "last_synced_at"]


class HostedZoneSerializer(serializers.ModelSerializer):
    account = AWSAccountSerializer(read_only=True)

    class Meta:
        model  = HostedZone
        fields = ["id", "zone_id", "name", "zone_type", "account", "record_count", "last_synced_at"]


class ZoneRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ZoneRecord
        fields = [
            "id", "zone", "name", "record_type", "ttl", "values",
            "is_alias", "alias_dns_name", "alias_hosted_zone_id",
            "alias_evaluate_target_health", "linked_ip",
        ]


class RegisteredDomainSerializer(serializers.ModelSerializer):
    class Meta:
        model  = RegisteredDomain
        fields = [
            "id", "account", "domain_name",
            "auto_renew", "transfer_lock", "expiry",
            "hosted_zone", "last_synced_at",
        ]


class ServiceLinkSerializer(serializers.ModelSerializer):
    assigned_object_type = serializers.SerializerMethodField()
    role_display         = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model  = ServiceLink
        fields = [
            "id", "assigned_object_type", "assigned_object_id",
            "service", "role", "role_display", "notes",
        ]

    def get_assigned_object_type(self, obj) -> str:
        return f"{obj.assigned_object_type.app_label}.{obj.assigned_object_type.model}"


class SyncLogSerializer(serializers.ModelSerializer):
    duration_seconds = serializers.SerializerMethodField()

    class Meta:
        model  = SyncLog
        fields = [
            "id", "account_id", "account_label",
            "started_at", "completed_at", "duration_seconds",
            "status", "message",
            "domains_seen", "domains_created", "domains_updated",
            "zones_seen", "zones_created", "zones_updated",
            "records_seen", "records_created", "records_updated", "records_deleted",
        ]
        read_only_fields = fields

    def get_duration_seconds(self, obj):
        d = obj.duration
        return d.total_seconds() if d else None
