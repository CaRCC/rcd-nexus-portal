from django import forms
from django.core.exceptions import ValidationError

from nexus.models import Institution, NewInstitutionRequest


class InstitutionForm(forms.ModelForm):
    template_name = "forms/grid.html"

    class Meta:
        model = Institution
        fields = [
            "name",
            "country",
            "state_or_province",
            "internet_domain",
            "student_pop",
            "undergrad_pop",
            "grad_pop",
            "research_expenditure",
            "carnegie_classification",
            "ipeds_sector",
            "ipeds_control",
            "ipeds_level",
            "ipeds_hbcu",
            "ipeds_tcu",
            "ipeds_land_grant",
            "ipeds_urbanization",
            "ipeds_size",
            "ipeds_region",
        ]


class NewInstitutionRequestForm(forms.ModelForm):
    template_name = "forms/grid.html"

    class Meta:
        model = NewInstitutionRequest
        exclude = [
            "requester",
        ]


class AffiliationRequestForm(forms.Form):
    email = forms.EmailField(
        label="Email",
        required=True,
    )

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        name, domain = email.split("@")

        try:
            institution = Institution.objects.get(internet_domain__endswith=domain)
        except Institution.DoesNotExist:
            raise ValidationError(
                "No institution found with that email domain. Fix any typos, or request a new institution be added to RCD Nexus using the above link."
            )

        if institution.has_cilogon_idp():
            raise ValidationError(
                f"{institution} supports CILogon authentication, so you must logout and login to RCD Nexus directly with your institutional account. If you have configured CILogon to remember your institutional selection, you may need to clear your browser cookies for 'cilogon.org'."
            )

        return cleaned_data
