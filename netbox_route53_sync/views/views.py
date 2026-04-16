from django.contrib.contenttypes.models import ContentType
from netbox.views import generic

from ..filtersets import (
    AWSAccountFilterSet, HostedZoneFilterSet, RegisteredDomainFilterSet,
    ServiceLinkFilterSet, SyncLogFilterSet, ZoneRecordFilterSet,
)
from ..forms import (
    AWSAccountFilterForm, HostedZoneFilterForm, RegisteredDomainFilterForm,
    ServiceLinkFilterForm, SyncLogFilterForm, ZoneRecordFilterForm,
)
from ..models import AWSAccount, HostedZone, RegisteredDomain, ServiceLink, SyncLog, ZoneRecord
from ..tables import (
    AWSAccountTable, HostedZoneTable, RegisteredDomainTable,
    ServiceLinkTable, SyncLogTable, ZoneRecordTable,
)


def _service_links_for(instance) -> ServiceLinkTable:
    """Return a ServiceLinkTable pre-filtered to the given object."""
    ct = ContentType.objects.get_for_model(instance)
    qs = ServiceLink.objects.filter(
        assigned_object_type=ct,
        assigned_object_id=instance.pk,
    ).select_related("service")
    return ServiceLinkTable(qs)


# ---------------------------------------------------------------------------
# AWSAccount
# ---------------------------------------------------------------------------

class AWSAccountListView(generic.ObjectListView):
    queryset       = AWSAccount.objects.all()
    table          = AWSAccountTable
    filterset      = AWSAccountFilterSet
    filterset_form = AWSAccountFilterForm
    template_name  = "netbox_route53_sync/awsaccount_list.html"


class AWSAccountView(generic.ObjectView):
    queryset      = AWSAccount.objects.prefetch_related("hosted_zones", "registered_domains")
    template_name = "netbox_route53_sync/awsaccount.html"

    def get_extra_context(self, request, instance):
        zones_table         = HostedZoneTable(instance.hosted_zones.all())
        domains_table       = RegisteredDomainTable(instance.registered_domains.all())
        service_links_table = _service_links_for(instance)
        return {
            "zones_table":          zones_table,
            "domains_table":        domains_table,
            "service_links_table":  service_links_table,
        }


# ---------------------------------------------------------------------------
# HostedZone
# ---------------------------------------------------------------------------

class HostedZoneListView(generic.ObjectListView):
    queryset       = HostedZone.objects.select_related("account")
    table          = HostedZoneTable
    filterset      = HostedZoneFilterSet
    filterset_form = HostedZoneFilterForm
    template_name  = "netbox_route53_sync/hostedzone_list.html"


class HostedZoneView(generic.ObjectView):
    queryset      = HostedZone.objects.select_related("account").prefetch_related("records")
    template_name = "netbox_route53_sync/hostedzone.html"

    def get_extra_context(self, request, instance):
        records_table       = ZoneRecordTable(instance.records.all())
        service_links_table = _service_links_for(instance)
        return {
            "records_table":       records_table,
            "service_links_table": service_links_table,
        }


# ---------------------------------------------------------------------------
# ZoneRecord
# ---------------------------------------------------------------------------

class ZoneRecordListView(generic.ObjectListView):
    queryset       = ZoneRecord.objects.select_related("zone", "zone__account")
    table          = ZoneRecordTable
    filterset      = ZoneRecordFilterSet
    filterset_form = ZoneRecordFilterForm
    template_name  = "netbox_route53_sync/zonerecord_list.html"


class ZoneRecordView(generic.ObjectView):
    queryset      = ZoneRecord.objects.select_related("zone", "zone__account", "linked_ip")
    template_name = "netbox_route53_sync/zonerecord.html"

    def get_extra_context(self, request, instance):
        return {"service_links_table": _service_links_for(instance)}


# ---------------------------------------------------------------------------
# RegisteredDomain
# ---------------------------------------------------------------------------

class RegisteredDomainListView(generic.ObjectListView):
    queryset       = RegisteredDomain.objects.select_related("account", "hosted_zone")
    table          = RegisteredDomainTable
    filterset      = RegisteredDomainFilterSet
    filterset_form = RegisteredDomainFilterForm
    template_name  = "netbox_route53_sync/registereddomain_list.html"


class RegisteredDomainView(generic.ObjectView):
    queryset      = RegisteredDomain.objects.select_related("account", "hosted_zone")
    template_name = "netbox_route53_sync/registereddomain.html"

    def get_extra_context(self, request, instance):
        return {"service_links_table": _service_links_for(instance)}


# ---------------------------------------------------------------------------
# ServiceLink
# ---------------------------------------------------------------------------

class ServiceLinkListView(generic.ObjectListView):
    queryset       = ServiceLink.objects.select_related("assigned_object_type", "service")
    table          = ServiceLinkTable
    filterset      = ServiceLinkFilterSet
    filterset_form = ServiceLinkFilterForm
    template_name  = "netbox_route53_sync/servicelink_list.html"


class ServiceLinkView(generic.ObjectView):
    queryset      = ServiceLink.objects.select_related("assigned_object_type", "service")
    template_name = "netbox_route53_sync/servicelink.html"


# ---------------------------------------------------------------------------
# SyncLog
# ---------------------------------------------------------------------------

class SyncLogListView(generic.ObjectListView):
    queryset       = SyncLog.objects.all()
    table          = SyncLogTable
    filterset      = SyncLogFilterSet
    filterset_form = SyncLogFilterForm
    template_name  = "netbox_route53_sync/synclog_list.html"


class SyncLogView(generic.ObjectView):
    queryset      = SyncLog.objects.all()
    template_name = "netbox_route53_sync/synclog.html"
