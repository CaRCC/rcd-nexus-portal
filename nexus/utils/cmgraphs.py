# from django.shortcuts import render
from django.db.models import Q, Case, Value, When
from functools import reduce
from operator import or_
from nexus.models import CapabilitiesAnswer, CapabilitiesAssessment, CapabilitiesTopic, Institution, RCDProfile
from nexus.forms import dataviz
#from django.http import JsonResponse
import pandas as pd
import plotly.express as px
import plotly.io as po
from django.db.models import Q

DEFAULT_WIDTH = 800
DEFAULT_HEIGHT = 600

colorPalette = {'allData':'#9F9F9F', 'EPSCoR':'#5ab4ac', 'nonEPSCoR':'#d8b365', 
                'errBars':'#bbb', 'lightErrBars':'#f5f5f5', 'bgColor':'#555',
                'RF':'#40bad2', 'DF': '#fab900', 'SWF':'#90bb23', 'SYF':'#ee7008', 'SPF':'#d5393d',
                'R1':'#2e75b6','R2':'#8bb8e1','AllButR1':'#d1e3f3','OtherAcad':'#d1e3f3','Other':'#e9f0f7',
                'Public':'#ffd966','Private':'#ec7728',
                'NotMSI':'#FFE699','HSI':'#C5E0B4','otherMSI':'#8FAADC',
                '2022':'#ffba5a', '2021':'#6aaa96', '2020':'#ada3d3'}

# QUESTION Why does this work?  Facings fixture defines the indices as 0-4, not 1-5
Facing_mapping = { 1: '<b>Researcher-<br>Facing</b>', 2: '<b>Data-<br>Facing</b>', 3: '<b>Software-<br>Facing</b>', 4 : '<b>System-<br>Facing</b>', 5: '<b>Strategy & Policy-<br>Facing</b>'}

def initCCMapping():
    mapping = {}
    mapping[0] = 'Other'
    mapping[99] = 'OtherAcad'
    for val in Institution.CarnegieClassificationChoices:
        mapping[int(val)] = val.label
    return mapping

cc_mapping = initCCMapping()


def computeMaxRange(averages, stddevs):
    if averages.empty or stddevs.empty :
        maxRange = 100
    else:
        maxRange = max(averages)+max(stddevs)
        maxRange = min(100, max(7, int((maxRange+.05)*10))*10)
    return maxRange

def getAllAnswers() :
    # Restrict to approved assessments
    answers = CapabilitiesAnswer.objects.filter(assessment__review_status=CapabilitiesAssessment.ReviewStatusChoices.APPROVED)
    # Get only the main answers (skip the domain coverage ones)
    answers = answers.exclude(question__topic__slug=CapabilitiesTopic.domain_coverage_slug)
    return answers

def getAllInstitutions() :
    # Any restrictions??? We need some kind of marker for test institutions
    # We need to find all the profiles and then get the associated institutions, not just get
    # all the institutions (most of which are imported from IPEDS data)
    return None

def filterInstitutions(dict):
    # TODO filter by population (contributor status: all vs contrib only)
    # TODO filter by cc
    # TODO filter by mission
    # TODO filter by pubpriv
    # TODO filter by region?? Have map, why do this? May allow reidentification
    # TODO filter by SIZE
    # TODO filter by epscor
    # TODO filter by msi???
    # TODO filter by year
    print("filterInstitutions NYI")
    return None, 81

def demographicsChartByCC(institutions, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    return '<br><h3 class="graphNYI">This chart is Not Yet Implemented</h3>'

def demographicsChartByMission(institutions, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    return '<br><h3 class="graphNYI">This chart is Not Yet Implemented</h3>'

def demographicsChartByPubPriv(institutions, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    return '<br><h3 class="graphNYI">This chart is Not Yet Implemented</h3>'

def demographicsChartByEPSCoR(institutions, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    return '<br><h3 class="graphNYI">This chart is Not Yet Implemented</h3>'

def demographicsChartByMSI(institutions, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    return '<br><h3 class="graphNYI">This chart is Not Yet Implemented</h3>'

# Not clear if we will do this one
#def demographicsChartBySize(institutions, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
#    return '<br><h3 class="graphNYI">This chart is Not Yet Implemented</h3>'

def demographicsChartByOrgModel(institutions, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    return '<br><h3 class="graphNYI">This chart is Not Yet Implemented</h3>'

def demographicsChartByReporting(institutions, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    return '<br><h3 class="graphNYI">This chart is Not Yet Implemented</h3>'


def filterAssessmentData(dict):
    """Translate URL query parameters into a filter for CapabilitiesAnswer objects."""
    answers = getAllAnswers()
    instCount = answers.values('assessment__id').distinct().count()
    #print("Before filtering have: ",answers.count(), " answers for: ",instCount," Institutions")

    if cc := dict.get('cc'):
        if len(cc) < len(dataviz.DataFilterForm.CC_CHOICES):   # Skip the filter if all are set (nothing to filter)
            values = set()

            if "R1" in cc:
                values.add(Institution.CarnegieClassificationChoices.R1)
            if "R2" in cc:
                values.add(Institution.CarnegieClassificationChoices.R2)

            filters = Q(assessment__profile__institution__carnegie_classification__in=values)
            if "otherac" in cc:
                # Note: this assumes that R1 and R2 are the numerically first two values in the CarnegieClassificationChoices
                filters |= Q(assessment__profile__institution__carnegie_classification__gt=Institution.CarnegieClassificationChoices.R2)

                # But some could also be null or 0 (which corresponds to "Other", such as labs, centers - not academic)
                filters |= Q(assessment__profile__institution__carnegie_classification=None)

            answers = answers.filter(filters)

    if missions := dict.get('mission'):
        if len(missions) < len(dataviz.DataFilterForm.MISSION_CHOICES):   # Skip the filter if all are set (nothing to filter)
            answers = answers.filter(assessment__profile__mission__in=missions)

    if pp := dict.get('pub_priv'):
        if len(pp) < len(dataviz.DataFilterForm.PUB_PRIV_CHOICES):   # Skip the filter if all are set (nothing to filter)
            values = set()
            if "pub" in pp:
                values.add(Institution.ControlChoices.PUBLIC)
            if "priv" in pp:
                ## values.add(Institution.ControlChoices.PRIVATE_FOR_PROFIT) # We have none of these yet, and they are different from "PRIVATE"
                values.add(Institution.ControlChoices.PRIVATE_NON_PROFIT)
            answers = answers.filter(assessment__profile__institution__ipeds_control__in=values)

    if eps := dict.get('epscor'):
        if len(eps) < len(dataviz.DataFilterForm.EPSCOR_CHOICES):   # Skip the filter if all are set (nothing to filter)
            answers = answers.filter(assessment__profile__institution__ipeds_epscor__in=eps)

    if msis := dict.get('msi'):
        # Filter by MSI: somewhat complicated. Choices are:
        #    hbcu: ipeds_hbcu = HBCUChoices.HBCU
        #    hsi: ipeds_hsi = HSIChoices.HSI
        #    otherMSI: ((ipeds_pbi = PBIChoices.PBI) OR (ipeds_tcu = TCUChoices.TCU) 
        #               OR (ipeds_aanapisi_annh = AANAPISI_ANNHChoices.AANAPISI_ANNH) OR (ipeds_msi = MSIChoices.MSI))
        #           AND [if not hbcu in choices](ipeds_hbcu = HBCUChoices.NOT_AN_HBCU)
        #           AND [if not hsi in choices](ipeds_hsi = HSIChoices.NOT_AN_HSI)
        #   notMSI: (ipeds_msi = MSIChoices.MSI)
        
        if len(msis) < len(dataviz.DataFilterForm.MSI_CHOICES):   # Skip the filter if all are set (nothing to filter)
            if not "notMSI" in msis:
                filters = Q(pk__in=[])
            else:
                filters = Q(assessment__profile__institution__ipeds_msi=Institution.MSIChoices.NOT_AN_MSI)
            if "hbcu" in msis:
                filters |= Q(assessment__profile__institution__ipeds_hbcu=Institution.HBCUChoices.HBCU)    # Add HBCUs
            if "hsi" in msis:
                filters |= Q(assessment__profile__institution__ipeds_hsi=Institution.HSIChoices.HSI)    # Add HSIs

            if "otherMSI" in cc:
                # BUG - Hawaii institutions are all AANAPISI_ANNHChoices.AANAPISI_ANNH, and admin shows them as such, but
                # this query does not return them! 
                filters |= Q(assessment__profile__institution__ipeds_pbi=Institution.PBIChoices.PBI)
                filters |= Q(assessment__profile__institution__ipeds_tcu=Institution.TCUChoices.TCU)
                filters |= Q(assessment__profile__institution__ipeds_aanapisi_annh=Institution.AANAPISI_ANNHChoices.AANAPISI_ANNH)
            answers = answers.filter(filters)

    if years := dict.get('year'):
        if len(years) < len(dataviz.DataFilterForm.YEAR_CHOICES):   # Skip the filter if all are set (nothing to filter)
            answers = answers.filter(assessment__profile__year__in=years)

    if sizes := dict.get('size'):
        if len(sizes) < len(dataviz.DataFilterForm.SIZE_CHOICES):   # Skip the filter if all are set (nothing to filter)
            answers = answers.filter(assessment__profile__institution__ipeds_size__in=sizes)

    if regions := dict.get('region'):
        if len(regions) < len(dataviz.DataFilterForm.REGION_CHOICES):   # Skip the filter if all are set (nothing to filter)
            answers = answers.filter(assessment__profile__institution__ipeds_region__in=regions)
 
    instCount = answers.values('assessment__id').distinct().count()
    #print("After filtering have: ",answers.count(), " answers for: ",instCount," Institutions")

    return answers, instCount

def allSummaryDataGraph(width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    return summaryDataGraph(getAllAnswers(), width, height)

def summaryDataGraph(answers, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
        #print("SummaryDataGraph with: ", answers.count()," answers")
        if (answers.count() == 0): 
            return None
        
        data = answers.aggregate_score('question__topic__facing').values('question__topic__facing','average','stddev')
        # Convert the queryset to a DataFrame
        df = pd.DataFrame(data)

        # Map the facings values to names
        df['question__topic__facing'] = df['question__topic__facing'].map(Facing_mapping)
        data = df

        # Rename the columns for clarity
        data = data.rename(columns={
                'average':'Average Values',
                'question__topic__facing' : 'Facings',
                'stddev' : 'Std Dev'
            })
        # print(data)

        # Compute a naive graph max and consider limiting the y axis (there is no simple way to compute the max of the sum) 
        # No - this is making the graphs jitter for comparison. 
        maxYRange = 100 #computeMaxRange(data['Average Values'], data['Std Dev'])
        # print("MaxYRange: "+str(maxYRange))

        data['Average Values'] *= 100
        data['Std Dev'] *= 100

        # Create a All Summary Data bar chart
        fig = px.bar(data, x='Facings', y= 'Average Values', error_y='Std Dev',width=width, height=height,color_discrete_sequence=[colorPalette['allData']]*5)

        fig.update_layout(
            margin_t=25,
            autosize=True, 
            xaxis=dict(title=dict(text='', font=dict(size=16, family='Arial'))),
            yaxis=dict(title=dict(text='', font=dict(size=16, family='Arial')), ticksuffix="%", range=[0, maxYRange], dtick=20),
            plot_bgcolor=colorPalette['bgColor']    )
        
        fig.update_traces( hovertemplate = 'Coverage: %{y:.1f}%')

        # Change the color of error bars
        fig.update_traces(error_y_color=colorPalette['errBars'],marker_line_color='black', marker_line_width=1.5, width=0.6)

        # Update the layout to set y-axis tickformat to percentages
        fig.update_layout(yaxis=dict(tickformat='%d% %'))  # Set tickformat to display percentages

        # Set the bar edge color
        #fig.update_traces(marker_line_color='black', marker_line_width=1.5)
        # fig.update_layout()
        # Set grid color and linestyle for y-axis
        fig.update_yaxes(gridcolor=colorPalette['errBars'], gridwidth=0.5, griddash='dot',zeroline=False)

        # Convert the figure to HTML including Plotly.js
        return po.to_html(fig, include_plotlyjs='cdn', full_html=True)

def facingSummaryDataGraph(answers, facing, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    return '<br><h3 class="graphNYI">This graph is Not Yet Implemented</h3>'
def simpleCC(cc) :
    if(cc=='R1')|(cc=='R2')|(cc=='Other'): return cc
    return 'OtherAcad'

def capsDataGraphByCC(answers, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    #print("capsDataGraphByCC with: ", answers.count()," answers")
    if (answers.count() == 0): 
        return None
    answers = answers.filter(assessment__profile__institution__carnegie_classification__isnull=False)
    annotatedAnswers = answers.annotate(simpleCC=Case(
        When(assessment__profile__institution__carnegie_classification=15, then=Value(15)),
        When(assessment__profile__institution__carnegie_classification=16, then=Value(16)),
        When(assessment__profile__institution__carnegie_classification=0, then=Value(0)),
        #When(assessment__profile__institution__carnegie_classification__isnull=True, then=Value(0)),
        default=Value(99) ))
    data = annotatedAnswers.aggregate_score('question__topic__facing','simpleCC').values('question__topic__facing','simpleCC','average','stddev')
    df = pd.DataFrame(data)     # Convert the queryset to a DataFrame
    # Map the facings values to names
    df['question__topic__facing'] = df['question__topic__facing'].map(Facing_mapping)
    df['simpleCC'] = df['simpleCC'].map(cc_mapping)

    # Multiply by 100 to display percentages
    df['average'] *= 100
    df['stddev'] *= 100

    # Rename the columns for clarity
    df= df.rename(columns={
            'question__topic__facing' : 'Facings',
            'average':'Average Value',
        })

    # Create a grouped bar chart
    fig = px.bar(df, x='Facings', y='Average Value',error_y='stddev',
                color='simpleCC', 
                color_discrete_map={'R1':colorPalette['R1'], 'R2':colorPalette['R2'],'OtherAcad':colorPalette['OtherAcad']},
                barmode='group', # Use 'group' for grouped bars
                labels={'question__topic__facing': '', 'average': '', 'simpleCC':'Carnegie Classification'},
                #title='Simple Carnegie Classification Facing Graphs',
                width=width, height=height )

    # Change font size and font type
    fig.update_layout(
        xaxis=dict(title=dict(text='', font=dict(size=16, family='Arial'))),
        yaxis=dict(title=dict(text='', font=dict(size=16, family='Arial')), ticksuffix="%", range=[0, 100], dtick=20),
        plot_bgcolor=colorPalette['bgColor'], 
        )
    fig.update_traces(error_y_color='#bbb', marker_line_color='black', marker_line_width=1.5,hovertemplate = 'Coverage: %{y:.1f}%')
    fig.update_yaxes(gridcolor=colorPalette['errBars'], gridwidth=0.5, griddash='dot',zeroline=False)

    return po.to_html(fig, include_plotlyjs='cdn', full_html=True)

def facingCapsDataGraphByCC(answers, facing, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    return '<br><h3 class="graphNYI">This graph is Not Yet Implemented</h3>'

def capsDataGraphByMission(answers, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    return '<br><h3 class="graphNYI">This graph is Not Yet Implemented</h3>'

def facingCapsDataGraphByMission(answers, facing, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    return '<br><h3 class="graphNYI">This graph is Not Yet Implemented</h3>'

def capsDataGraphByPubPriv(answers, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    return '<br><h3 class="graphNYI">This graph is Not Yet Implemented</h3>'

def facingCapsDataGraphByPubPriv(answers, facing, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    return '<br><h3 class="graphNYI">This graph is Not Yet Implemented</h3>'

def capsDataGraphByEPSCoR(answers, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    return '<br><h3 class="graphNYI">This graph is Not Yet Implemented</h3>'

def facingCapsDataGraphByEPSCoR(answers, facing, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    return '<br><h3 class="graphNYI">This graph is Not Yet Implemented</h3>'

def capsDataGraphByMSI(answers, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    return '<br><h3 class="graphNYI">This graph is Not Yet Implemented</h3>'

def facingCapsDataGraphByMSI(answers, facing, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    return '<br><h3 class="graphNYI">This graph is Not Yet Implemented</h3>'

def capsDataGraphByOrgModel(answers, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    return '<br><h3 class="graphNYI">This graph is Not Yet Implemented</h3>'

def facingCapsDataGraphByOrgModel(answers, facing, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    return '<br><h3 class="graphNYI">This graph is Not Yet Implemented</h3>'

def capsDataGraphByReporting(answers, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    return '<br><h3 class="graphNYI">This graph is Not Yet Implemented</h3>'

def facingCapsDataGraphByReporting(answers, facing, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    return '<br><h3 class="graphNYI">This graph is Not Yet Implemented</h3>'

