from django import forms

from nexus.models import RCDProfile, RCDProfileMemberInvite


class RCDProfileForm(forms.ModelForm):
    template_name = "forms/grid.html"

    class Meta:
        model = RCDProfile
        exclude = [
            "institution",
            "year",
            "created_by",
            "users",
            "archived",
        ]
        widgets = {
            "mission":forms.RadioSelect,
        }

    def customize_choices(self, request, inst):
        self.fields["institution_subunit"].choices = [
            (subunit, subunit)
            for subunit in inst.profiles.values_list("institution_subunit", flat=True)
        ]


class RCDProfileMemberInviteForm(forms.ModelForm):
    template_name = "forms/grid.html"

    class Meta:
        model = RCDProfileMemberInvite
        fields = []

    email_to = forms.CharField(
        widget=forms.Textarea,
        required=False,
        help_text="An optional list of emails to send invitations to, one per line.",
    )

    accept_terms = forms.BooleanField(
        label="Acknowledgement",
        required=True,
        help_text="I acknowledge that invited users may be able to view and modify RCD Nexus assessments and other data attributed to the institution.",
    )
