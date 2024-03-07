# from django.shortcuts import render
from django.db.models import Q, Case, Value, When, Count, F
from functools import reduce
from operator import or_
from math import ceil
from nexus.models import CapabilitiesAnswer, CapabilitiesAssessment, CapabilitiesTopic, Institution, RCDProfile
from nexus.forms import dataviz
#from django.http import JsonResponse
import pandas as pd
import plotly.express as px
import plotly.io as po
from django.db.models import Q
from nexus.utils import cmgraphs

PIE_SIZE_SCALE = 0.75
DEFAULT_PIE_WIDTH=cmgraphs.DEFAULT_WIDTH*PIE_SIZE_SCALE
DEFAULT_PIE_HEIGHT=cmgraphs.DEFAULT_HEIGHT*PIE_SIZE_SCALE

def getAllProfiles(pop='contrib', years=None) :
    # TODO: We need some kind of marker for test institutions
    # Find all the profiles since some of the filters and graphs are profile info.
    profiles = RCDProfile.objects.all()
    if not years is None:
        # print('getAllProfiles filtering to years: ',years)
        profiles = profiles.filter(year__in=years)
    
    # print('getAllProfiles filtering to contributors')
    if pop == 'contrib':
        profiles = profiles.filter(capabilities_assessment__review_status=CapabilitiesAssessment.ReviewStatusChoices.APPROVED)
    # Now ensure we only have the latest profile for each institution for the given set of years
    profiles = profiles.order_by('institution', '-year').distinct('institution')
    return profiles

# Translate URL query parameters into a filter for Profile objects
def filterProfiles(dict):
    profiles=None
    # Check whether all users or just contributors
    if not (pop := dict.get('population')):
        pop = 'contrib'
    # Have to handle years specially since it can impact which is the "latest" profile. 
    if years := dict.get('year'):
        if len(years) < len(dataviz.DataFilterForm.YEAR_CHOICES):   # Skip the filter if all are set (nothing to filter)
            profiles = getAllProfiles(pop, years)                   # filters on years, and then gets answers for latest assessment for each institution

    # if we did not handle the special case of years, get all the answers normally
    if(profiles is None):
        profiles = getAllProfiles(pop)                               # gets answers for latest assessment for each institution
    if cc := dict.get('cc'):
        if len(cc) < len(dataviz.DataFilterForm.CC_CHOICES):   # Skip the filter if all are set (nothing to filter)
            values = set()

            if "R1" in cc:
                values.add(Institution.CarnegieClassificationChoices.R1)
            if "R2" in cc:
                values.add(Institution.CarnegieClassificationChoices.R2)

            filters = Q(institution__carnegie_classification__in=values)
            if "otherac" in cc:
                # Note: this assumes that R1 and R2 are the numerically first two values in the CarnegieClassificationChoices
                filters |= Q(institution__carnegie_classification__gt=Institution.CarnegieClassificationChoices.R2)

                # But some could also be null or 0 (which corresponds to "Other", such as labs, centers - not academic)
                filters |= Q(institution__carnegie_classification=None)

            profiles = profiles.filter(filters)

    if missions := dict.get('mission'):
        if len(missions) < len(dataviz.DataFilterForm.MISSION_CHOICES):   # Skip the filter if all are set (nothing to filter)
            profiles = profiles.filter(mission__in=missions)

    if pp := dict.get('pub_priv'):
        if len(pp) < len(dataviz.DataFilterForm.PUB_PRIV_CHOICES):   # Skip the filter if all are set (nothing to filter)
            values = set()
            if "pub" in pp:
                values.add(Institution.ControlChoices.PUBLIC)
            if "priv" in pp:
                ## values.add(Institution.ControlChoices.PRIVATE_FOR_PROFIT) # We have none of these yet, and they are different from "PRIVATE"
                values.add(Institution.ControlChoices.PRIVATE_NON_PROFIT)
            profiles = profiles.filter(institution__ipeds_control__in=values)

    if eps := dict.get('epscor'):
        if len(eps) < len(dataviz.DataFilterForm.EPSCOR_CHOICES):   # Skip the filter if all are set (nothing to filter)
            profiles = profiles.filter(institution__ipeds_epscor__in=eps)

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
                filters = Q(institution__ipeds_msi=Institution.MSIChoices.NOT_AN_MSI)
            if "hbcu" in msis:
                filters |= Q(institution__ipeds_hbcu=Institution.HBCUChoices.HBCU)    # Add HBCUs
            if "hsi" in msis:
                filters |= Q(institution__ipeds_hsi=Institution.HSIChoices.HSI)    # Add HSIs

            if "otherMSI" in msis:
                # TODO: add exclude annotations for HBCU and HSIs. 
                filters |= Q(institution__ipeds_pbi=Institution.PBIChoices.PBI)
                filters |= Q(institution__ipeds_tcu=Institution.TCUChoices.TCU)
                filters |= Q(institution__ipeds_aanapisi_annh=Institution.AANAPISI_ANNHChoices.AANAPISI_ANNH)
            profiles = profiles.filter(filters)

    if sizes := dict.get('size'):
        if len(sizes) < len(dataviz.DataFilterForm.SIZE_CHOICES):   # Skip the filter if all are set (nothing to filter)
            profiles = profiles.filter(institution__ipeds_size__in=sizes)

    if regions := dict.get('region'):
        if len(regions) < len(dataviz.DataFilterForm.REGION_CHOICES):   # Skip the filter if all are set (nothing to filter)
            profiles = profiles.filter(institution__ipeds_region__in=regions)
 
    #print("After filtering have: ",profiles.count(), " profiles")
    return profiles

def applyStandardPieFormatting(fig):
    fig.update_layout(showlegend=False, margin_t=20,margin_b=20,margin_l=20,margin_r=20,autosize=True,)
    fig.update_traces(sort=False, direction='clockwise', hovertemplate='%{label}: %{value:.0f} institutions', 
                      textposition='inside', texttemplate='%{label}: %{percent:.0%}', textfont_size=18,
                  marker=dict(line=dict(color=cmgraphs.colorPalette['errBars'], width=1.5)))

def demographicsChartByCC(profiles, width=DEFAULT_PIE_WIDTH, height=DEFAULT_PIE_HEIGHT):
    # For this chart, we'll include the "Other" institutions that have a Null CC value
    annotatedProfiles = profiles.annotate(simpleCC=Case(
        When(institution__carnegie_classification__lt=Institution.CarnegieClassificationChoices.R1, 
                then=Value(cmgraphs.CC_BACC)),
        When(institution__carnegie_classification__gte=Institution.CarnegieClassificationChoices.R1, 
             institution__carnegie_classification__lte=Institution.CarnegieClassificationChoices.M3, 
                then=F('institution__carnegie_classification')),
        When(institution__carnegie_classification__gt=Institution.CarnegieClassificationChoices.M3, 
                then=Value(cmgraphs.CC_BACC)),
        #When(institution__carnegie_classification=0, then=Value(cmgraphs.CC_MISC)),            # Properly Other, but this sorts better
        #When(institution__carnegie_classification__isnull=True, then=Value(cmgraphs.CC_MISC)), # Properly Other, but this sorts better
        default=Value(cmgraphs.CC_MISC) ))
    simpleCCList = annotatedProfiles.values('simpleCC')
    data = simpleCCList.values('simpleCC')
    df = pd.DataFrame(data)     # Convert the queryset to a DataFrame
    #print(df)
    counts = df.groupby('simpleCC').size()      # Don't sort_values(ascending=False); keep in CC order
    counts = counts.rename(cmgraphs.cc_mapping)

    # Create a grouped bar chart
    fig = px.pie(counts, values=counts.array, names=counts.index, width=width, height=height, color=counts.index, 
                color_discrete_map=cmgraphs.simple_cc_palette )
    applyStandardPieFormatting(fig)
    
    return po.to_html(fig, include_plotlyjs='cdn', full_html=True)


def demographicsChartByMission(profiles, width=DEFAULT_PIE_WIDTH, height=DEFAULT_PIE_HEIGHT):
    annotatedProfiles = profiles.annotate(mission2=Case(
        When(mission__isnull=True, then=Value(cmgraphs.VALUE_UNKNOWN)),
        default=F('mission') ))
    data = annotatedProfiles.values('mission2')
    df = pd.DataFrame(data)     # Convert the queryset to a DataFrame
    counts = df.groupby('mission2').size()
    counts = counts.rename(cmgraphs.mission_mapping)

    # Create a grouped bar chart
    fig = px.pie(counts, values=counts.array, names=counts.index, width=width, height=height, color=counts.index, 
                color_discrete_map=cmgraphs.mission_palette)
    applyStandardPieFormatting(fig)
    
    return po.to_html(fig, include_plotlyjs='cdn', full_html=True)

def demographicsChartByPubPriv(profiles, width=DEFAULT_PIE_WIDTH, height=DEFAULT_PIE_HEIGHT):
    data = profiles.values('institution__ipeds_control')
    df = pd.DataFrame(data)     # Convert the queryset to a DataFrame
    counts = df.groupby('institution__ipeds_control').size()
    counts = counts.rename(cmgraphs.pubpriv_mapping)

    # Create a grouped bar chart
    fig = px.pie(counts, values=counts.array, names=counts.index, width=width, height=height, color=counts.index, 
                color_discrete_map=cmgraphs.pub_priv_palette)
    applyStandardPieFormatting(fig)
    
    return po.to_html(fig, include_plotlyjs='cdn', full_html=True)

def demographicsChartByEPSCoR(profiles, width=DEFAULT_PIE_WIDTH, height=DEFAULT_PIE_HEIGHT):
    data = profiles.values('institution__ipeds_epscor')
    df = pd.DataFrame(data)     # Convert the queryset to a DataFrame
    counts = df.groupby('institution__ipeds_epscor').size()
    counts = counts.rename(cmgraphs.epscor_mapping)

    # Create a grouped bar chart
    fig = px.pie(counts, values=counts.array, names=counts.index, width=width, height=height, color=counts.index, 
                color_discrete_map={Institution.EPSCORChoices.EPSCOR.label: cmgraphs.colorPalette['EPSCoR'], 
                                        Institution.EPSCORChoices.NOT_EPSCOR.label: cmgraphs.colorPalette['nonEPSCoR']})
    applyStandardPieFormatting(fig)
    
    return po.to_html(fig, include_plotlyjs='cdn', full_html=True)

def demographicsChartByMSI(profiles, width=DEFAULT_PIE_WIDTH, height=DEFAULT_PIE_HEIGHT):
    #data = profiles.values('institution__ipeds_msi')

    annotatedProfiles = profiles.annotate(simpleMSI=Case(
        # TODO: change case statements to have ranges and just map the Baccs and others
        # Have the default be to use the CC value
        When(institution__ipeds_tcu=Institution.TCUChoices.TCU,
                then=Value(cmgraphs.MSI_TCU)),
        When(institution__ipeds_hbcu=Institution.HBCUChoices.HBCU, 
                then=Value(cmgraphs.MSI_HBCU_PBI)),
        When(institution__ipeds_pbi=Institution.PBIChoices.PBI,
                then=Value(cmgraphs.MSI_HBCU_PBI)),
        When(institution__ipeds_hsi=Institution.HSIChoices.HSI,
                then=Value(cmgraphs.MSI_HSI)),
        When(institution__ipeds_aanapisi_annh=Institution.AANAPISI_ANNHChoices.AANAPISI_ANNH,
                then=Value(cmgraphs.MSI_AA)),
        When(institution__ipeds_msi=Institution.MSIChoices.MSI,
                then=Value(cmgraphs.MSI_OTHER)),
        default=Value(cmgraphs.MSI_NOT) ))
    simpleMSIList = annotatedProfiles.values('simpleMSI')
    data = simpleMSIList.values('simpleMSI')

    df = pd.DataFrame(data)     # Convert the queryset to a DataFrame
    print(df)
    counts = df.groupby('simpleMSI').size()
    counts = counts.rename(cmgraphs.simple_msi_mapping)

    # Create a grouped bar chart
    fig = px.pie(counts, values=counts.array, names=counts.index, width=width, height=height, color=counts.index, 
                color_discrete_map=cmgraphs.simple_msi_palette )
    applyStandardPieFormatting(fig)
    
    return po.to_html(fig, include_plotlyjs='cdn', full_html=True)

# Not clear if we will do this one
#def demographicsChartBySize(profiles, width=DEFAULT_PIE_WIDTH, height=DEFAULT_HEIGHT):
#    return '<br><h3 class="graphNYI">This chart is Not Yet Implemented</h3>'

def demographicsChartByOrgModel(profiles, width=DEFAULT_PIE_WIDTH, height=DEFAULT_PIE_HEIGHT):
    annotatedProfiles = profiles.annotate(structure2=Case(
        When(structure__isnull=True, then=Value(cmgraphs.VALUE_UNKNOWN)),
        default=F('structure') ))
    data = annotatedProfiles.values('structure2')
    df = pd.DataFrame(data)     # Convert the queryset to a DataFrame
    counts = df.groupby('structure2').size()
    counts = counts.rename(cmgraphs.structure_mapping)

    # Create a grouped bar chart
    fig = px.pie(counts, values=counts.array, names=counts.index, width=width, height=height, color=counts.index, 
                color_discrete_map=cmgraphs.structure_palette)
    applyStandardPieFormatting(fig)
    
    return po.to_html(fig, include_plotlyjs='cdn', full_html=True)
def demographicsChartByReporting(profiles, width=DEFAULT_PIE_WIDTH, height=DEFAULT_PIE_HEIGHT):
    return '<br><h3 class="graphNYI">This chart is Not Yet Implemented</h3>'

def scatterChart(answers, instCount, width=cmgraphs.DEFAULT_WIDTH, height=cmgraphs.DEFAULT_HEIGHT):
    if (answers.count() == 0): 
        return None
    
    data = answers.aggregate_score('question__topic__facing','assessment__profile__institution'). \
        values('question__topic__facing','assessment__profile__institution','average')

    df= pd.DataFrame(data)
    df['question__topic__facing'] = df['question__topic__facing'].map(cmgraphs.Facing_mapping) # Map the facings to names

    # clip values to [0,1] since the collaboration boost/discount can push coverage over 1.0 and under 0
    df['average'] =  df['average'].clip(lower=0.0, upper=1.0)
    # Multiply by 100 to display percentages
    df['average'] *= 100

    # Rename the columns for clarity
    df =  df.rename(columns={
            'question__topic__facing' : 'Facings',
            'assessment__profile__institution' :'Inst',
            'average':'Average Values',
        })
    nInstsRange = [i for i in range(1, 1+int(instCount))]
    instIndex = pd.Index(nInstsRange+nInstsRange+nInstsRange+nInstsRange+nInstsRange)
    df.loc[:, 'Inst'] = instIndex
    #print('Scatter df: ',df)

    # Create a scatter chart
    fig = px.scatter( df, x='Inst', y='Average Values',
                    color='Facings',
                    # color_discrete_map=scatterPlotcolorMap,
                    color_discrete_sequence=cmgraphs.scatterPlotColorSeq,
                    labels=None,
                    width=800, height=550)
    
    #fig.update_layout(yaxis={'visible': False, 'showticklabels': False})
    roundedInstCount = ceil(instCount/5)*5
    xdtick = 5 if roundedInstCount<25 else 10
    fig.update_layout(
        xaxis=dict(range=[0, roundedInstCount], visible=True, showticklabels=True, dtick=xdtick, color='white'),
        xaxis_title=dict(text='<b>Institutions</b>', font=dict(size=14, color=cmgraphs.colorPalette['bgColor']), standoff=0),
        yaxis=dict(ticksuffix="%", range=[0, 100], dtick=20),
        yaxis_title=dict(text='<b>Coverage</b>', font=dict(size=14, color=cmgraphs.colorPalette['bgColor'])),
        plot_bgcolor=cmgraphs.colorPalette['bgColor'], 
        margin_t=25,autosize=True,
        legend_title_text=''
        )
    msize = 5 + 100/instCount   # scale the marker size up for fewer results
    fig.update_traces(marker={'size': msize})


    # Convert the figure to HTML including Plotly.js
    return po.to_html(fig, include_plotlyjs='cdn', full_html=True)
