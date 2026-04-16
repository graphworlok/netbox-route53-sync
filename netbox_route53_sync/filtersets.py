import django_filters

from .choices import RecordTypeChoices, SyncStatusChoices, ZoneTypeChoices
from .models import AWSAccount, HostedZone, RegisteredDomain, SyncLog, ZoneRecord


class AWSAccountFilterSet(django_filters.FilterSet):
    q = django_filters.CharFilter(method="search", label="Search")

    class Meta:
        model  = AWSAccount
        fields = ["account_id"]

    def search(self, qs, name, value):
        return qs.filter(account_id__icontains=value) | qs.filter(label__icontains=value)


class HostedZoneFilterSet(django_filters.FilterSet):
    q         = django_filters.CharFilter(method="search", label="Search")
    zone_type = django_filters.ChoiceFilter(choices=ZoneTypeChoices)
    account   = django_filters.ModelChoiceFilter(queryset=AWSAccount.objects.all())

    class Meta:
        model  = HostedZone
        fields = ["zone_type", "account"]

    def search(self, qs, name, value):
        return qs.filter(name__icontains=value) | qs.filter(zone_id__icontains=value)


class ZoneRecordFilterSet(django_filters.FilterSet):
    q           = django_filters.CharFilter(method="search", label="Search")
    record_type = django_filters.ChoiceFilter(choices=RecordTypeChoices)
    is_alias    = django_filters.BooleanFilter()
    zone        = django_filters.ModelChoiceFilter(queryset=HostedZone.objects.all())

    class Meta:
        model  = ZoneRecord
        fields = ["record_type", "is_alias", "zone"]

    def search(self, qs, name, value):
        return qs.filter(name__icontains=value)


class RegisteredDomainFilterSet(django_filters.FilterSet):
    q             = django_filters.CharFilter(method="search", label="Search")
    auto_renew    = django_filters.BooleanFilter()
    transfer_lock = django_filters.BooleanFilter()
    account       = django_filters.ModelChoiceFilter(queryset=AWSAccount.objects.all())

    class Meta:
        model  = RegisteredDomain
        fields = ["auto_renew", "transfer_lock", "account"]

    def search(self, qs, name, value):
        return qs.filter(domain_name__icontains=value)


class SyncLogFilterSet(django_filters.FilterSet):
    q      = django_filters.CharFilter(method="search", label="Search")
    status = django_filters.ChoiceFilter(choices=SyncStatusChoices)

    class Meta:
        model  = SyncLog
        fields = ["account_id", "status"]

    def search(self, qs, name, value):
        return qs.filter(account_id__icontains=value) | qs.filter(account_label__icontains=value)
