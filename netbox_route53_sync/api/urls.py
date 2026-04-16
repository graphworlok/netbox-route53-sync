from netbox.api.routers import NetBoxRouter

from .views import (
    AWSAccountViewSet, HostedZoneViewSet, RegisteredDomainViewSet,
    ServiceLinkViewSet, SyncLogViewSet, ZoneRecordViewSet,
)

router = NetBoxRouter()
router.register("accounts",           AWSAccountViewSet)
router.register("hosted-zones",       HostedZoneViewSet)
router.register("zone-records",       ZoneRecordViewSet)
router.register("registered-domains", RegisteredDomainViewSet)
router.register("service-links",      ServiceLinkViewSet)
router.register("sync-logs",          SyncLogViewSet)

urlpatterns = router.urls
