from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.viewsets import GenericViewSet

from ..models import AWSAccount, HostedZone, RegisteredDomain, ServiceLink, SyncLog, ZoneRecord
from .serializers import (
    AWSAccountSerializer, HostedZoneSerializer, RegisteredDomainSerializer,
    ServiceLinkSerializer, SyncLogSerializer, ZoneRecordSerializer,
)


class AWSAccountViewSet(RetrieveModelMixin, ListModelMixin, GenericViewSet):
    queryset         = AWSAccount.objects.all()
    serializer_class = AWSAccountSerializer


class HostedZoneViewSet(RetrieveModelMixin, ListModelMixin, GenericViewSet):
    queryset         = HostedZone.objects.select_related("account")
    serializer_class = HostedZoneSerializer


class ZoneRecordViewSet(RetrieveModelMixin, ListModelMixin, GenericViewSet):
    queryset         = ZoneRecord.objects.select_related("zone")
    serializer_class = ZoneRecordSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        zone_id = self.request.query_params.get("zone_id")
        if zone_id:
            qs = qs.filter(zone__zone_id=zone_id)
        record_type = self.request.query_params.get("type")
        if record_type:
            qs = qs.filter(record_type=record_type.upper())
        return qs


class RegisteredDomainViewSet(RetrieveModelMixin, ListModelMixin, GenericViewSet):
    queryset         = RegisteredDomain.objects.select_related("account", "hosted_zone")
    serializer_class = RegisteredDomainSerializer


class ServiceLinkViewSet(RetrieveModelMixin, ListModelMixin, GenericViewSet):
    queryset         = ServiceLink.objects.select_related("assigned_object_type", "service")
    serializer_class = ServiceLinkSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        # Allow filtering by ?object_type=hostedzone&object_id=42
        object_type = self.request.query_params.get("object_type")
        object_id   = self.request.query_params.get("object_id")
        if object_type:
            qs = qs.filter(assigned_object_type__model=object_type.lower())
        if object_id:
            qs = qs.filter(assigned_object_id=object_id)
        return qs


class SyncLogViewSet(RetrieveModelMixin, ListModelMixin, GenericViewSet):
    queryset         = SyncLog.objects.all()
    serializer_class = SyncLogSerializer
