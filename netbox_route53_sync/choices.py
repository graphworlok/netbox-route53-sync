from utilities.choices import ChoiceSet


class SyncStatusChoices(ChoiceSet):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"    # completed with some per-zone errors
    FAILED  = "failed"

    CHOICES = [
        (PENDING, "Pending", "secondary"),
        (RUNNING, "Running", "warning"),
        (SUCCESS, "Success", "success"),
        (PARTIAL, "Partial", "orange"),
        (FAILED,  "Failed",  "danger"),
    ]


class ZoneTypeChoices(ChoiceSet):
    PUBLIC  = "public"
    PRIVATE = "private"

    CHOICES = [
        (PUBLIC,  "Public",  "success"),
        (PRIVATE, "Private", "secondary"),
    ]


class RecordTypeChoices(ChoiceSet):
    """Standard DNS record types supported by Route53."""
    A     = "A"
    AAAA  = "AAAA"
    CNAME = "CNAME"
    MX    = "MX"
    NS    = "NS"
    PTR   = "PTR"
    SOA   = "SOA"
    SPF   = "SPF"
    SRV   = "SRV"
    TXT   = "TXT"
    CAA   = "CAA"
    DS    = "DS"
    NAPTR = "NAPTR"
    ALIAS = "ALIAS"    # Route53 alias record (not a standard DNS type)

    CHOICES = [
        (A,     "A",     "blue"),
        (AAAA,  "AAAA",  "purple"),
        (CNAME, "CNAME", "teal"),
        (MX,    "MX",    "orange"),
        (NS,    "NS",    "secondary"),
        (PTR,   "PTR",   "secondary"),
        (SOA,   "SOA",   "secondary"),
        (SPF,   "SPF",   "secondary"),
        (SRV,   "SRV",   "green"),
        (TXT,   "TXT",   "cyan"),
        (CAA,   "CAA",   "yellow"),
        (DS,    "DS",    "secondary"),
        (NAPTR, "NAPTR", "secondary"),
        (ALIAS, "ALIAS", "indigo"),
    ]
