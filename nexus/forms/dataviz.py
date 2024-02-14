import datetime
from django import forms
from django.core.exceptions import ValidationError
from nexus.models.rcd_profiles import RCDProfile
from nexus.models.ipeds_classification import IPEDSMixin

# Define an extended MultipleChoiceField that can have an All|None UI built in
class AllNoneMultipleChoiceField(forms.MultipleChoiceField):
    showAllNone=True
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

# Note: we define the form with all the possible fields, and then call initFilterTree to control which fields are shown
# This initFilterTree method needs the includes, excludes, and the POST context. 
# For a POST, creating from the request should init everything correctly, but then we have to recreate the form
# with the cleaned data, so the form is unbound and this mutable (so we can change the label to hide it in the template)

# Still need to figure out how to render a button to show and hide each list set.
# May need to use this approach: https://stackoverflow.com/questions/10366745/django-form-field-grouping to
# group the filter tree form fields separately from the other vix hoices that run across the top. 
# For now, all the fields are in the filter tree. 
class DataFilterForm(forms.Form):
    # Must pass in a string (e.g., rcd_profiles.MissionChoices.RESEARCHESSENTIAL.label)
    def getShortMissionChoice(label):
        #The Choices all have the main label marked in <b> tags, at the start. We just extract that
        return label[3:label.find("</b>")]
    
    hasViewChoices=False  # indicates to template that this version of Form includes View choices

    POPULATION="Population"
    POP_CHOICES = (
        ("all","All Users"), 
        ("contrib","Contributors"),
    )
    CARN_CLASS="Carnegie Classification"
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

    ORG_MODEL="Organizational Model"
    ORG_MODEL_CHOICES = (
        (RCDProfile.StructureChoices.STANDALONE.value,RCDProfile.StructureChoices.STANDALONE.label),
        (RCDProfile.StructureChoices.EMBEDDED.value,RCDProfile.StructureChoices.EMBEDDED.label),
        (RCDProfile.StructureChoices.DECENTRALIZED.value,RCDProfile.StructureChoices.DECENTRALIZED.label),
        (RCDProfile.StructureChoices.NONE.value,RCDProfile.StructureChoices.NONE.label),
    )

    REPORTING="Reporting structure"
    REPORTING_CHOICES = (
        (RCDProfile.OrgChartChoices.INFOTECH.value,RCDProfile.OrgChartChoices.INFOTECH.label),
        (RCDProfile.OrgChartChoices.RESEARCH.value,RCDProfile.OrgChartChoices.RESEARCH.label),
        (RCDProfile.OrgChartChoices.ACADEMIA.value,RCDProfile.OrgChartChoices.ACADEMIA.label),
        (RCDProfile.OrgChartChoices.INSTITUTE.value,RCDProfile.OrgChartChoices.INSTITUTE.label),
        (RCDProfile.OrgChartChoices.OTHER.value,RCDProfile.OrgChartChoices.OTHER.label),
    )
    PUB_PRIV="Public/Private"
    PUB_PRIV_CHOICES = (
        ("pub","Public"),
        ("priv","Private"),
        # In theory we should add private for profit, but we have yet to see any and it would just be clutter
    )
    EPSCOR="EPSCoR Status"
    EPSCOR_CHOICES = (     # Need to think about this since we may only be able to say MSI or not in our dataset. 
        (IPEDSMixin.EPSCORChoices.EPSCOR,IPEDSMixin.EPSCORChoices.EPSCOR.label),
        (IPEDSMixin.EPSCORChoices.NOT_EPSCOR,IPEDSMixin.EPSCORChoices.NOT_EPSCOR.label),
    )

    MSI="Minority Serving Status"
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
    def buildYearChoiceList():
        choices = []
        thisyear = datetime.date.today().year
        for year in range(2020, thisyear+1):
            yrStr = str(year)
            choices.append((year, yrStr))
        return choices

    YEAR_CHOICES = buildYearChoiceList()

    RESEARCH_EXP="Research Exp."

    # Add the Data View controls for charts, and for caps model data
    CHART_VIEWS="Chart View"
    CHART_VIEW_CHOICES = (
        ("sum","Summary"),
        ("cc",CARN_CLASS),
        ("mission",MISSION),
        ("pub_priv",PUB_PRIV),
        ("epscor",EPSCOR),
        ("msi",MSI),
        ("orgmodel",ORG_MODEL),
        ("reporting",REPORTING),
    )

    FACINGS="Facing Detail"
    FACINGS_CHOICES = (
        ("all","Summary for All Facings"),
        ("rf","Researcher-Facing Topics"),
        ("df","Data-Facing Topics"),
        ("swf","Software-Facing Topics"),
        ("syf","Systems-Facing Topics"),
        ("spf","Strategy & Policy-Facing Topics"),
    )

    CAPS_FEATURE="Capability Feature"
    CAPS_FEATURE_CHOICES = (
        ("cov","Computed Coverage"),
        ("avail","Availability Across Inst."),
        ("sol","Service Operating Level"),
        ("eng","Community Engagement & Collab."),
    )

    BENCHMARK="Benchmark my Data"

    NOT_FILTERS = CHART_VIEWS+", "+FACINGS+", "+CAPS_FEATURE+", "+BENCHMARK

    # Note that we are omitting ORG_MODEL and REPORTING for now, unless and until someone asks for this info
    INCLUDE_ALL={POPULATION, CARN_CLASS, MISSION, PUB_PRIV, EPSCOR, MSI, SIZE, BY_YEAR, REGION, RESEARCH_EXP}
    CHARTS_INCLUDE_ALL={POPULATION, CARN_CLASS, MISSION, PUB_PRIV, EPSCOR, MSI, SIZE, BY_YEAR, REGION, RESEARCH_EXP, CHART_VIEWS}
    # Omit the "Population" choice when viewing contributor data
    INCLUDE_ALL_CONTRIBS={CARN_CLASS, MISSION, PUB_PRIV, EPSCOR, MSI, SIZE, BY_YEAR, REGION, RESEARCH_EXP}
    # Omit the "Population" choice when viewing contributor data, and add the detail views
    CAPS_DATA_INCLUDE_ALL={CARN_CLASS, MISSION, PUB_PRIV, EPSCOR, MSI, SIZE, BY_YEAR, REGION, RESEARCH_EXP, CHART_VIEWS, FACINGS, CAPS_FEATURE, BENCHMARK}

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

    mission = AllNoneMultipleChoiceField(
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

    region = AllNoneMultipleChoiceField(
        label=REGION,
        choices=REGION_CHOICES,
        initial = [c[0] for c in REGION_CHOICES],   # Default to all selected
        widget=forms.CheckboxSelectMultiple(attrs={"class":"toggle"}),
        help_text="Filter by US Region or Canada",
    )

    size = AllNoneMultipleChoiceField(
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

    msi = AllNoneMultipleChoiceField(
        label=MSI,
        choices=MSI_CHOICES,
        initial = [c[0] for c in MSI_CHOICES],   # Default to all selected
        widget=forms.CheckboxSelectMultiple(),
        help_text="Filter by Minority-Serving status",
    )

    year = AllNoneMultipleChoiceField(
        label=BY_YEAR,
        choices=YEAR_CHOICES,
        initial = [c[0] for c in YEAR_CHOICES],   # Default to all selected
        widget=forms.CheckboxSelectMultiple(),
        help_text="Filter by the Year a Profile was created or an Assessment was Contributed",
    )

    """ These are more important to be able to show, that to use as filters. 
    org_model = forms.MultipleChoiceField(
        label=ORG_MODEL,
        choices=ORG_MODEL_CHOICES,
        initial = [c[0] for c in ORG_MODEL_CHOICES],   # Default to all selected
        widget=forms.CheckboxSelectMultiple(),
        help_text="Filter by Organizational Model",
    )

    reporting = forms.MultipleChoiceField(
        label=REPORTING,
        choices=REPORTING_CHOICES,
        initial = [c[0] for c in REPORTING_CHOICES],   # Default to all selected
        widget=forms.CheckboxSelectMultiple(),
        help_text="Filter by Reporting Structure (where in the Org Chart the program sits)",
    )
    """

    chart_views = forms.ChoiceField(
        label=CHART_VIEWS,
        choices=CHART_VIEW_CHOICES,
        initial = [0],   # Default to CARN_CLASS
        help_text="Select the data you want to compare in the chart",
    )

    facings = forms.ChoiceField(
        label=FACINGS,
        choices=FACINGS_CHOICES,
        initial = [0],   # Default to Summary
        help_text="Choose the Facing detail you want to explore",
    )

    caps_feature = forms.ChoiceField(
        label=CAPS_FEATURE,
        choices=CAPS_FEATURE_CHOICES,
        initial = [0],   # Default to Computed coverage
        help_text="Choose overall coverage or just one lens",
    )

    benchmark = forms.BooleanField(
        label=BENCHMARK,
        initial = False,    # Default to just show data (no benchmarking)
        required=False,     # Cannot require this or would always have benchmarking on
        help_text="Check if you want to overlay institutional data for benchmarking",
    )
    

    # Need to add support for YEAR, and for RESEARCH EXPENDITURES

    #Should we add Land Grant, and others?

    # Modify the DataFilterForm filter elements to reflect the context
    def filtertree(self, includes=None, excludes=None):
        # We prefix labels with "skip" to preserve the label (for debugging and just in case)
        if (includes and self.POPULATION not in includes) or (excludes and self.POPULATION in excludes):
            self.fields['population'].label = "skip:"+self.fields['population'].label
        if (includes and self.CARN_CLASS not in includes) or (excludes and self.CARN_CLASS in excludes):
            self.fields['cc'].label = "skip"+self.fields['cc'].label
        if (includes and self.MISSION not in includes) or (excludes and self.MISSION in excludes):
            self.fields['mission'].label = "skip"+self.fields['mission'].label
        """
        if (includes and self.ORG_MODEL not in includes) or (excludes and self.ORG_MODEL in excludes):
            self.fields['org_model'].label = "skip"
        if (includes and self.REPORTING not in includes) or (excludes and self.REPORTING in excludes):
            self.fields['reporting'].label = "skip"
        """
        if (includes and self.PUB_PRIV not in includes) or (excludes and self.PUB_PRIV in excludes):
            self.fields['pub_priv'].label = "skip"+self.fields['pub_priv'].label
        if (includes and self.REGION not in includes) or (excludes and self.REGION in excludes):
            self.fields['region'].label = "skip"+self.fields['region'].label
        if (includes and self.SIZE not in includes) or (excludes and self.SIZE in excludes):
            self.fields['size'].label = "skip"+self.fields['size'].label
        if (includes and self.EPSCOR not in includes) or (excludes and self.EPSCOR in excludes):
            self.fields['epscor'].label = "skip"+self.fields['epscor'].label
        if (includes and self.MSI not in includes) or (excludes and self.MSI in excludes):
            self.fields['msi'].label = "skip"+self.fields['msi'].label

        # Handle the view choices. Note that we will never "restore" Views on the fly so just replace vs. prefix labels, with "skip"
        self.hasViewChoices = False  # default, unless we have ANY of the view choices
        if (includes and self.CHART_VIEWS not in includes) or (excludes and self.CHART_VIEWS in excludes):
            self.fields['chart_views'].label = "skip"
        else: 
            self.hasViewChoices = True
        if (includes and self.FACINGS not in includes) or (excludes and self.FACINGS in excludes):
            self.fields['facings'].label = "skip"
        else: 
            self.hasViewChoices = True
        if (includes and self.CAPS_FEATURE not in includes) or (excludes and self.CAPS_FEATURE in excludes):
            self.fields['caps_feature'].label = "skip"
        else: 
            self.hasViewChoices = True
        if (includes and self.BENCHMARK not in includes) or (excludes and self.BENCHMARK in excludes):
            self.fields['benchmark'].label = "skip"
        else: 
            self.hasViewChoices = True

