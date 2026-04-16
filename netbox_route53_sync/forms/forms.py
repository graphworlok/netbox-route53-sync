from django import forms

from ..choices import RecordTypeChoices, ServiceLinkRoleChoices, SyncStatusChoices, ZoneTypeChoices


class AWSAccountFilterForm(forms.Form):
    q = forms.CharField(required=False, label="Search",
        widget=forms.TextInput(attrs={"placeholder": "Account ID or label…"}))


class HostedZoneFilterForm(forms.Form):
    q = forms.CharField(required=False, label="Search",
        widget=forms.TextInput(attrs={"placeholder": "Zone name or ID…"}))
    zone_type = forms.ChoiceField(required=False,
        choices=[("", "Any type")] + list(ZoneTypeChoices), label="Type")


class ZoneRecordFilterForm(forms.Form):
    q = forms.CharField(required=False, label="Search",
        widget=forms.TextInput(attrs={"placeholder": "Record name…"}))
    record_type = forms.ChoiceField(required=False,
        choices=[("", "Any type")] + list(RecordTypeChoices), label="Record Type")
    is_alias = forms.NullBooleanSelect()


class RegisteredDomainFilterForm(forms.Form):
    q = forms.CharField(required=False, label="Search",
        widget=forms.TextInput(attrs={"placeholder": "Domain name…"}))
    auto_renew    = forms.NullBooleanField(required=False, label="Auto Renew")
    transfer_lock = forms.NullBooleanField(required=False, label="Transfer Lock")


class ServiceLinkForm(forms.Form):
    """
    Used when creating or editing a ServiceLink from a detail page.
    Full ModelForm would be defined if edit views are added later.
    """
    pass


class ServiceLinkFilterForm(forms.Form):
    q = forms.CharField(required=False, label="Search",
        widget=forms.TextInput(attrs={"placeholder": "Service name or notes…"}))
    role = forms.ChoiceField(required=False,
        choices=[("", "Any role")] + list(ServiceLinkRoleChoices), label="Role")


class SyncLogFilterForm(forms.Form):
    q = forms.CharField(required=False, label="Search",
        widget=forms.TextInput(attrs={"placeholder": "Account ID or label…"}))
    status = forms.ChoiceField(required=False,
        choices=[("", "Any status")] + list(SyncStatusChoices), label="Status")
