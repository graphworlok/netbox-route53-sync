from django.urls import path

from . import views

app_name = "netbox_route53_sync"

urlpatterns = [
    # AWS Accounts
    path("accounts/",                   views.AWSAccountListView.as_view(),      name="awsaccount_list"),
    path("accounts/<int:pk>/",          views.AWSAccountView.as_view(),          name="awsaccount"),

    # Hosted Zones
    path("hosted-zones/",               views.HostedZoneListView.as_view(),      name="hostedzone_list"),
    path("hosted-zones/<int:pk>/",      views.HostedZoneView.as_view(),          name="hostedzone"),

    # Zone Records
    path("zone-records/",               views.ZoneRecordListView.as_view(),      name="zonerecord_list"),
    path("zone-records/<int:pk>/",      views.ZoneRecordView.as_view(),          name="zonerecord"),

    # Registered Domains
    path("registered-domains/",         views.RegisteredDomainListView.as_view(), name="registereddomain_list"),
    path("registered-domains/<int:pk>/", views.RegisteredDomainView.as_view(),    name="registereddomain"),

    # Sync Logs
    path("sync-logs/",                  views.SyncLogListView.as_view(),         name="synclog_list"),
    path("sync-logs/<int:pk>/",         views.SyncLogView.as_view(),             name="synclog"),
]
