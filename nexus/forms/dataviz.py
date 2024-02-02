from django import forms
from django.core.exceptions import ValidationError
from nexus.models.rcd_profiles import RCDProfile
from nexus.models.ipeds_classification import IPEDSMixin

# For a multiple with checkboxes: 
# my_field = forms.MultipleChoiceField(choices=SOME_CHOICES, widget=forms.CheckboxSelectMultiple())
# FOr radio select:
# RadioSelect (see this for alignment in template: https://stackoverflow.com/questions/60914671/align-radio-buttons-vertically-when-they-are-on-the-right-side-of-the-label)
# Define the form with all the possible fields, and then call initFilterTree to control which fields are shown
# This initFilterTree method needs the includes, excludes, and the POST context. 
# For a POST, creating from the request should init everything correctly

# Must pass in a string (e.g., rcd_profiles.MissionChoices.RESEARCHESSENTIAL.label)
def getShortMissionChoice(label):
    #The Choices all have the main label marked in <b> tags. We just extract that
    return label[3:label.find("</b>")]

POPULATION="Population"
POP_CHOICES = (
    ("all","All Users"), 
    ("contrib","Contributors"),
)
CARN_CLASS="Carnegie Class."
CC_CHOICES=(
    ("R1","R1"),
    ("R2","R2"),
    ("otherac","Other Acad."),
)
MISSION="Mission"
MISSION_CHOICES = (     # Need to think about this since we may only be able to say MSI or not in our dataset. 
    (RCDProfile.MissionChoices.RESEARCHESSENTIAL.value,getShortMissionChoice(RCDProfile.MissionChoices.RESEARCHESSENTIAL.label)),
    (RCDProfile.MissionChoices.RESEARCHFAVORED.value,getShortMissionChoice(RCDProfile.MissionChoices.RESEARCHFAVORED.label)),
    (RCDProfile.MissionChoices.BALANCED.value,getShortMissionChoice(RCDProfile.MissionChoices.BALANCED.label)),
    (RCDProfile.MissionChoices.TEACHINGFAVORED.value,getShortMissionChoice(RCDProfile.MissionChoices.TEACHINGFAVORED.label)),
    (RCDProfile.MissionChoices.TEACHINGESSENTIAL.value,getShortMissionChoice(RCDProfile.MissionChoices.TEACHINGESSENTIAL.label)),
)

PUB_PRIV="Public/Private"
PUB_PRIV_CHOICES = (
    ("pub","Public"),
    ("priv","Private"),
    # In theory we should add private for profit, but we have yet to see any and it would just be clutter
)
EPSCOR="EPSCoR"
EPSCOR_CHOICES = (     # Need to think about this since we may only be able to say MSI or not in our dataset. 
    (IPEDSMixin.EPSCORChoices.EPSCOR,IPEDSMixin.EPSCORChoices.EPSCOR.label),
    (IPEDSMixin.EPSCORChoices.NOT_EPSCOR,IPEDSMixin.EPSCORChoices.NOT_EPSCOR.label),
)

MSI="Minority Serving"
MSI_CHOICES = (     # Need to think about this since we may only be able to say MSI or not in our dataset. 
    ("hbcu","HBCU"),
    ("hsi","HSI"),
    ("otherMSI","Other MSI"),
    ("notMSI","Not Minority Serving"),
)

REGION="Region"
REGION_CHOICES = (     # Need to think about this since we may only be able to say MSI or not in our dataset. 
    # (IPEDSMixin.RegionChoices.SERVICE_SCHOOLS,IPEDSMixin.RegionChoices.SERVICE_SCHOOLS.label), None of these, so filter for now
    (IPEDSMixin.RegionChoices.NEW_ENGLAND,IPEDSMixin.RegionChoices.NEW_ENGLAND.label),
    (IPEDSMixin.RegionChoices.MID_EAST,IPEDSMixin.RegionChoices.MID_EAST.label),
    (IPEDSMixin.RegionChoices.GREAT_LAKES,IPEDSMixin.RegionChoices.GREAT_LAKES.label),
    (IPEDSMixin.RegionChoices.PLAINS,IPEDSMixin.RegionChoices.PLAINS.label),
    (IPEDSMixin.RegionChoices.SOUTHEAST,IPEDSMixin.RegionChoices.SOUTHEAST.label),
    (IPEDSMixin.RegionChoices.SOUTHWEST,IPEDSMixin.RegionChoices.SOUTHWEST.label),
    (IPEDSMixin.RegionChoices.ROCKY_MOUNTAINS,IPEDSMixin.RegionChoices.ROCKY_MOUNTAINS.label),
    (IPEDSMixin.RegionChoices.FAR_WEST,IPEDSMixin.RegionChoices.FAR_WEST.label),
    (IPEDSMixin.RegionChoices.OTHER_U_S_JURISDICTIONS,"Other U.S."),        # "Other U.S. jurisdictions" is too long
    (IPEDSMixin.RegionChoices.CANADA,IPEDSMixin.RegionChoices.CANADA.label),
)

SIZE="Size"
SIZE_CHOICES = (     # Need to think about this since we may only be able to say MSI or not in our dataset. 
    (IPEDSMixin.SizeChoices.UNDER_1000,IPEDSMixin.SizeChoices.UNDER_1000.label),
    (IPEDSMixin.SizeChoices.BTW_1000_4999,IPEDSMixin.SizeChoices.BTW_1000_4999.label),
    (IPEDSMixin.SizeChoices.BTW_5000_9999,IPEDSMixin.SizeChoices.BTW_5000_9999.label),
    (IPEDSMixin.SizeChoices.BTW_10000_19999,IPEDSMixin.SizeChoices.BTW_10000_19999.label),
    (IPEDSMixin.SizeChoices.ABOVE_20000,IPEDSMixin.SizeChoices.ABOVE_20000.label),
)

BY_YEAR="By Year"
RESEARCH_EXP="Research Exp."

INCLUDE_ALL={POPULATION, CARN_CLASS, MISSION, PUB_PRIV, EPSCOR, MSI, BY_YEAR, REGION, RESEARCH_EXP}
INCLUDE_ALL_CONTRIBS={CARN_CLASS, MISSION, PUB_PRIV, EPSCOR, MSI, BY_YEAR, REGION, RESEARCH_EXP}

# Still need to figure out how to render a button to show and hide each list set.
# May need to use this approach: https://stackoverflow.com/questions/10366745/django-form-field-grouping to
# group the filter tree form fields separately from the other vix hoices that run across the top. 
# For now, all the fields are in the filter tree. 
class DataFilterForm(forms.Form):
    population = forms.ChoiceField(
        label=POPULATION,
        choices=POP_CHOICES,
        initial="all",
        widget=forms.RadioSelect(),
        help_text="Show data for All institutions or just Contributors",
    )
    cc = forms.MultipleChoiceField(
        label=CARN_CLASS,
        choices=CC_CHOICES,
        initial = [c[0] for c in CC_CHOICES],   # Default to all selected
        widget=forms.CheckboxSelectMultiple(),
        #validators=[require_min_one],
        help_text="Filter by Institution (Carnegie) Type",
    )

    mission = forms.MultipleChoiceField(
        label=MISSION,
        choices=MISSION_CHOICES,
        initial = [c[0] for c in MISSION_CHOICES],   # Default to all selected
        widget=forms.CheckboxSelectMultiple(),
        help_text="Filter by Institutional Mission",
    )

    pub_priv = forms.MultipleChoiceField(
        label=PUB_PRIV,
        choices=PUB_PRIV_CHOICES,
        initial = [c[0] for c in PUB_PRIV_CHOICES],   # Default to all selected
        widget=forms.CheckboxSelectMultiple(),
        help_text="Filter by Institutional Control (Public or Private)",
    )

    region = forms.MultipleChoiceField(
        label=REGION,
        choices=REGION_CHOICES,
        initial = [c[0] for c in REGION_CHOICES],   # Default to all selected
        widget=forms.CheckboxSelectMultiple(attrs={"class":"toggle"}),
        help_text="Filter by US Region or Canada",
    )

    size = forms.MultipleChoiceField(
        label=SIZE,
        choices=SIZE_CHOICES,
        initial = [c[0] for c in SIZE_CHOICES],   # Default to all selected
        widget=forms.CheckboxSelectMultiple(),
        help_text="Filter by Size (total number of students)",
    )

    epscor = forms.MultipleChoiceField(
        label=EPSCOR,
        choices=EPSCOR_CHOICES,
        initial = [c[0] for c in EPSCOR_CHOICES],   # Default to all selected
        widget=forms.CheckboxSelectMultiple(),
        help_text="Filter by EPSCoR eligibility",
    )

    msi = forms.MultipleChoiceField(
        label=MSI,
        choices=MSI_CHOICES,
        initial = [c[0] for c in MSI_CHOICES],   # Default to all selected
        widget=forms.CheckboxSelectMultiple(),
        help_text="Filter by Minority-Serving status",
    )

    #Things to add: Land Grant, etc. etc. 


    # Modify the DataFilterForm to reflect the context
    def filtertree(self, includes=None, excludes=None):
        if (includes and POPULATION not in includes) or (excludes and POPULATION in excludes):
            self.fields['population'].label = "skip"
        if (includes and CARN_CLASS not in includes) or (excludes and CARN_CLASS in excludes):
            self.fields['cc'].label = "skip"
        if (includes and MISSION not in includes) or (excludes and MISSION in excludes):
            self.fields['mission'].label = "skip"
        if (includes and PUB_PRIV not in includes) or (excludes and PUB_PRIV in excludes):
            self.fields['pub_priv'].label = "skip"
        if (includes and REGION not in includes) or (excludes and REGION in excludes):
            self.fields['region'].label = "skip"
        if (includes and SIZE not in includes) or (excludes and SIZE in excludes):
            self.fields['size'].label = "skip"
        if (includes and EPSCOR not in includes) or (excludes and EPSCOR in excludes):
            self.fields['epscor'].label = "skip"
        if (includes and MSI not in includes) or (excludes and MSI in excludes):
            self.fields['msi'].label = "skip"

        """
        if (includes and BY_YEAR in includes) or (excludes and not BY_YEAR in excludes):
            children = []
            thisyear = datetime.date.today().year
            for year in range(2020, thisyear):
                yrStr = str(year)
                children.append(FilterChoice(label=yrStr, valueName=yrStr, checked=True))
            tree.addChild(FilterCategory(label=BY_YEAR, paramName="year", collapsed=True, children=children))
        
        return tree
        """