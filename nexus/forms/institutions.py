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
            "ipeds_pbi",
            "ipeds_tcu",
            "ipeds_hsi",
            "ipeds_aanapisi_annh",
            "ipeds_msi",
            "ipeds_epscor",
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

        # institution = Institution.objects.get(internet_domain__endswith=domain)
        institution = None

        # Search for a matching existing institution, starting with the full domain and working up to the TLD.
        domain_parts = domain.split(".")
        searched_part_count = len(domain_parts)
        while searched_part_count >= 2:
            inst_list = Institution.objects.filter(internet_domain=".".join(domain_parts[-searched_part_count:]))
            if inst_list.count() > 1 :
                raise ValidationError(
                    "We couldn't resolve this email domain to a unique IPEDS institution. Please email capsmodel-help@carcc.org to proceed."
                )
            elif inst_list.count() > 0 :
                institution = inst_list.first()
                break
            searched_part_count -= 1

        if not institution:
            raise ValidationError(
                "No institution found with that email domain. Fix any typos, or request a new institution be added to the CaRCC RCD Nexus portal using the above link."
            )

        if institution.has_cilogon_idp():
            raise ValidationError(
                f"{institution} supports CILogon authentication, so you must logout and login to the CaRCC RCD Nexus portal directly with your institutional account. If you have configured CILogon to remember your institutional selection, you may need to clear your browser cookies for 'cilogon.org'."
            )
        
        # Pass the found institution through to the handler so we don't have to go through the hunt again. 
        cleaned_data['institution'] = institution

        return cleaned_data
