from django import forms

from nexus.models import CapabilitiesAnswer


class CapabilitiesAnswerForm(forms.ModelForm):
    template_name = "forms/helptext-tooltip.html"

    class Meta:
        model = CapabilitiesAnswer
        fields = [
            "score_deployment",
            "score_supportlevel",
            "score_collaboration",
            "not_applicable",
            "priority",
            "work_notes",
        ]


class CapabilitiesAssessmentSubmitForm(forms.Form):
    template_name = "forms/grid.html"

    attest = forms.BooleanField(
        label="Attest",
        required=True,
        help_text="I/we confirm that the data is accurate to the best of my/our knowledge.",
    )
    contribute_data = forms.BooleanField(
        label="Contribute",
        required=True,
        help_text="I/we agree that our assessment data may be shared (anonymously and in aggregate form) as part of \
                RCD Capabilties Model community datasets.",
    )
    list_inst = forms.BooleanField(
        label="List Institution",
        required=True,
        help_text="I/we agree that our institution may be listed among the community dataset contributors.",
    )