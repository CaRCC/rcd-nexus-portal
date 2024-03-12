# from django.shortcuts import render
from django.db.models import Q, Case, Value, When
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

DEFAULT_WIDTH = 800
DEFAULT_HEIGHT = 600

VALUE_UNKNOWN = "unknown"
VALUE_UNKNOWN_LABEL = "Unknown"

colorPalette = {'allData':'#9F9F9F', 'EPSCoR':'#5ab4ac', 'nonEPSCoR':'#d8b365', 
                'errBars':'#bbb', 'lightErrBars':'#f5f5f5', 'bgColor':'#555',
                'RF':'#40bad2', 'DF': '#fab900', 'SWF':'#90bb23', 'SYF':'#ee7008', 'SPF':'#d5393d',
                'R1':'#2e75b6','R2':'#8bb8e1','R3':'#d1e3f3','AllButR1':'#d1e3f3','OtherAcad':'#d1e3f3','Other':'#e9f0f7',
                'M1':'#95A472','M2':'#C8E087','M3':'#DDFCAD','Bacc':'#F7EF81',
                'Centralized':'#A37C40','School':'#98473E','Decentralized':'#B49082','None':'#D6C3C9',
                'Public':'#ffd966','Private':'#ec7728',
                'NotMSI':'#8FB8DE','HSI':'#586F6B','HBCU':'#CFE795','AA':'#F7EF81','TCU':'#D4C685','otherMSI':'#D0CFEC',
                VALUE_UNKNOWN_LABEL:'#8d99ae',
                '2022':'#ffba5a', '2021':'#6aaa96', '2020':'#ada3d3'}

scatterPlotcolorMap = {'RT':colorPalette['RF'],'DT':colorPalette['DF'], 'SWT':colorPalette['SWF'],
                                    'SYT':colorPalette['SYF'], 'SPT':colorPalette['SPF']}
scatterPlotColorSeq = [colorPalette['RF'],colorPalette['DF'],colorPalette['SWF'],colorPalette['SYF'],colorPalette['SPF']]

# QUESTION Why does this work?  Facings fixture defines the indices as 0-4, not 1-5
Facing_mapping = { 1: '<b>Researcher-<br>Facing</b>', 2: '<b>Data-<br>Facing</b>', 3: '<b>Software-<br>Facing</b>', 4 : '<b>System-<br>Facing</b>', 5: '<b>Strategy & Policy-<br>Facing</b>'}

CC_OTHER = 0
CC_OTHERACAD = 99
CC_MISC = 100
CC_BACC = 98

def initCCMapping():
    mapping = {}
    mapping[CC_MISC] = 'Other'
    mapping[CC_OTHER] = 'Other'
    mapping[CC_OTHERACAD] = 'OtherAcad'
    mapping[CC_BACC] = 'Bacc'
    for val in Institution.CarnegieClassificationChoices:
        mapping[int(val)] = val.label
    return mapping

cc_mapping = initCCMapping()

simple_cc_palette = {'R1':colorPalette['R1'], 'R2':colorPalette['R2'], 'R3':colorPalette['R3'],
                      'M1':colorPalette['M1'], 'M2':colorPalette['M2'], 'M3':colorPalette['M3'],
                      'Bacc':colorPalette['Bacc'],'Other':'white'}

MSI_NOT = 0
MSI_HSI = 1
MSI_HBCU_PBI = 2
MSI_AA = 3
MSI_TCU = 4
MSI_OTHER = 9

simple_msi_mapping = {
    MSI_NOT: 'Not an MSI',
    MSI_HSI: 'Hispanic-Serving',
    MSI_HBCU_PBI: 'HBCU/PBI',
    MSI_AA: 'AANAPISI or ANNH',
    MSI_TCU: 'Tribal College',
    MSI_OTHER: 'Other MSI',
    }
simple_msi_palette = {'Not an MSI': colorPalette['NotMSI'], 'Hispanic-Serving': colorPalette['HSI'], 'HBCU/PBI': colorPalette['HBCU'], 
                    'AANAPISI or ANNH': colorPalette['AA'], 'Tribal College': colorPalette['TCU'], 'Other MSI': colorPalette['otherMSI'] }

# Define a dictionary to map Pub/Priv (control) values to names
# We are simplifying the PRIVATE group for now since we have no for-profits using the tools
pubpriv_mapping = {
    Institution.ControlChoices.PUBLIC: Institution.ControlChoices.PUBLIC.label,
    Institution.ControlChoices.PRIVATE_NON_PROFIT: 'Private'    
    }
pub_priv_palette = {'Public':colorPalette['Public'], 'Private':colorPalette['Private'],}

# Define a dictionary to map EPSCoR values to names
epscor_mapping = {
    Institution.EPSCORChoices.EPSCOR: Institution.EPSCORChoices.EPSCOR.label,
    Institution.EPSCORChoices.NOT_EPSCOR: Institution.EPSCORChoices.NOT_EPSCOR.label,    
    }

# Define a dictionary to map MSI values to names
msi_mapping = {
    Institution.MSIChoices.MSI: Institution.MSIChoices.MSI.label,
    Institution.MSIChoices.NOT_AN_MSI: Institution.MSIChoices.NOT_AN_MSI.label,    
    }

# Define a dictionary to map Mission values to names
mission_mapping = {
    RCDProfile.MissionChoices.RESEARCHESSENTIAL: RCDProfile.getShortMissionChoice(RCDProfile.MissionChoices.RESEARCHESSENTIAL.label),
    RCDProfile.MissionChoices.RESEARCHFAVORED: RCDProfile.getShortMissionChoice(RCDProfile.MissionChoices.RESEARCHFAVORED.label),
    RCDProfile.MissionChoices.BALANCED: RCDProfile.getShortMissionChoice(RCDProfile.MissionChoices.BALANCED.label),
    RCDProfile.MissionChoices.TEACHINGFAVORED: RCDProfile.getShortMissionChoice(RCDProfile.MissionChoices.TEACHINGFAVORED.label),
    RCDProfile.MissionChoices.TEACHINGESSENTIAL: RCDProfile.getShortMissionChoice(RCDProfile.MissionChoices.TEACHINGESSENTIAL.label),
    VALUE_UNKNOWN: VALUE_UNKNOWN_LABEL
    }
mission_palette = {
    RCDProfile.getShortMissionChoice(RCDProfile.MissionChoices.RESEARCHESSENTIAL.label):'#e29578',
    RCDProfile.getShortMissionChoice(RCDProfile.MissionChoices.RESEARCHFAVORED.label):'#ffddd2',
    RCDProfile.getShortMissionChoice(RCDProfile.MissionChoices.BALANCED.label):'#edf6f9',
    RCDProfile.getShortMissionChoice(RCDProfile.MissionChoices.TEACHINGFAVORED.label):'#83c5be',
    RCDProfile.getShortMissionChoice(RCDProfile.MissionChoices.TEACHINGESSENTIAL.label):'#e29578',
    VALUE_UNKNOWN_LABEL:colorPalette[VALUE_UNKNOWN_LABEL]
    }

# Define a dictionary to map Structure values to names
structure_mapping = {
    RCDProfile.StructureChoices.STANDALONE: 'Centralized',
    RCDProfile.StructureChoices.EMBEDDED: 'In a School/Dept.',
    RCDProfile.StructureChoices.DECENTRALIZED: 'Decentralized across units',
    RCDProfile.StructureChoices.NONE: 'No organized support',
    VALUE_UNKNOWN: VALUE_UNKNOWN_LABEL
    }
structure_palette = {
    'Centralized':'#dda15e',
    'In a School/Dept.':'#fefae0',
    'Decentralized across units':'#283618',
    'No organized support': '#606c38',
    VALUE_UNKNOWN_LABEL:colorPalette[VALUE_UNKNOWN_LABEL]
    }



def computeMaxRange(averages, stddevs):
    if averages.empty or stddevs.empty :
        maxRange = 100
    else:
        maxRange = max(averages)+max(stddevs)
        maxRange = min(100, max(7, int((maxRange+.05)*10))*10)
    return maxRange

def getAllAnswers(years=None) :
    # Restrict to approved assessments
    profiles = RCDProfile.objects.filter(capabilities_assessment__review_status=CapabilitiesAssessment.ReviewStatusChoices.APPROVED)
    if not years is None:
        # print('getAllAnswers filtering to years: ',years)
        profiles = profiles.filter(year__in=years)
    # Now ensure we only have the latest profile for each institution for the given set of years
    profiles = profiles.order_by('institution', '-year').distinct('institution')
    #print("getAllAnswers found: ",profiles.count()," distinct non-superseded profiles")
    answers = CapabilitiesAnswer.objects.filter(assessment__profile__in=profiles)
    # Get only the main answers (skip the domain coverage ones)
    answers = answers.exclude(question__topic__slug=CapabilitiesTopic.domain_coverage_slug)
    #print(answers.count())
    instCount = answers.values('assessment__id').distinct().count()

    return answers, instCount

# Translate URL query parameters into a filter for CapabilitiesAnswer objects
# Note that we skip filtering when all values are chosen. This is both more efficient, and moreover
# ensures that we do not filter out all the Null values (e.g., for mission) on older profiles. 
def filterAssessmentData(dict):

    # We normally start with the latest profiles for each institution, but if we are filtering on years, we
    # have to handle that specially by passing in the years we are interested in.
    answers=None
    if years := dict.get('year'):
        if len(years) < len(dataviz.DataFilterForm.YEAR_CHOICES):   # Skip the filter if all are set (nothing to filter)
            answers = getAllAnswers(years)[0]                       # filters on years, and then gets answers for latest assessment for each institution

    # if we did not handle the special case, get all the answers normally
    if(answers is None):
        answers = getAllAnswers()[0]                                # gets answers for latest assessment for each institution

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

            if "otherMSI" in msis:
                # TODO: add exclude annotations for HBCU and HSIs. 
                filters |= Q(assessment__profile__institution__ipeds_pbi=Institution.PBIChoices.PBI)
                filters |= Q(assessment__profile__institution__ipeds_tcu=Institution.TCUChoices.TCU)
                filters |= Q(assessment__profile__institution__ipeds_aanapisi_annh=Institution.AANAPISI_ANNHChoices.AANAPISI_ANNH)
            answers = answers.filter(filters)

    if sizes := dict.get('size'):
        if len(sizes) < len(dataviz.DataFilterForm.SIZE_CHOICES):   # Skip the filter if all are set (nothing to filter)
            answers = answers.filter(assessment__profile__institution__ipeds_size__in=sizes)

    if regions := dict.get('region'):
        if len(regions) < len(dataviz.DataFilterForm.REGION_CHOICES):   # Skip the filter if all are set (nothing to filter)
            answers = answers.filter(assessment__profile__institution__ipeds_region__in=regions)
 
    instCount = answers.values('assessment__id').distinct().count()
    #print("After filtering have: ",answers.count(), " answers for: ",instCount," Institutions")

    return answers, instCount

def applyStandardVBarFormatting(fig, width=None):
    # Apply standard font size and font type
    fig.update_layout(
        xaxis=dict(title=dict(text='', font=dict(size=16, family='Arial'))),
        yaxis=dict(title=dict(text='', font=dict(size=16, family='Arial')), ticksuffix="%", range=[0, 100], dtick=20),
        plot_bgcolor=colorPalette['bgColor'], 
        margin_t=25,autosize=True,
        legend_title_text=''
        )
    fig.update_traces(error_y_color=colorPalette['errBars'], 
                      marker_line_color='black', marker_line_width=1.5,width=width, hovertemplate = 'Coverage: %{y:.1f}%')
    fig.update_yaxes(gridcolor=colorPalette['errBars'], gridwidth=0.5, griddash='dot',zeroline=False)


def allSummaryDataGraph(width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    answers, instCount = getAllAnswers()
    return summaryDataGraph(answers, width, height), instCount

def summaryDataGraph(answers, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
        #print("SummaryDataGraph with: ", answers.count()," answers")
        #instCount = answers.values('assessment__id').distinct().count()
        #print("SummaryDataGraph with: ", answers.count()," answers for: ",instCount," Institutions")
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
        print(data)

        # Compute a naive graph max and consider limiting the y axis (there is no simple way to compute the max of the sum) 
        # No - this is making the graphs jitter for comparison. 
        maxYRange = 100 #computeMaxRange(data['Average Values'], data['Std Dev'])
        # print("MaxYRange: "+str(maxYRange))

        data['Average Values'] *= 100
        data['Std Dev'] *= 100

        # Create a All Summary Data bar chart
        fig = px.bar(data, x='Facings', y= 'Average Values', error_y='Std Dev',width=width, height=height,color_discrete_sequence=[colorPalette['allData']]*5)
        applyStandardVBarFormatting(fig, width=0.6)
        
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
    # For this graph, we will ignore the "Other" institutions (labs, etc.) which have Null values for CC
    answers = answers.filter(assessment__profile__institution__carnegie_classification__isnull=False)
    annotatedAnswers = answers.annotate(simpleCC=Case(
        When(assessment__profile__institution__carnegie_classification=15, then=Value(15)),
        When(assessment__profile__institution__carnegie_classification=16, then=Value(16)),
        When(assessment__profile__institution__carnegie_classification=0, then=Value(0)),
        # When(assessment__profile__institution__carnegie_classification__isnull=True, then=Value(0)),
        default=Value(99) ))
    data = annotatedAnswers.aggregate_score('question__topic__facing','simpleCC').values('question__topic__facing','simpleCC','average','stddev')
    df = pd.DataFrame(data)     # Convert the queryset to a DataFrame
    # Map the facings values to names
    df['question__topic__facing'] = df['question__topic__facing'].map(Facing_mapping)
    df['simpleCC'] = df['simpleCC'].map(cc_mapping)

    # clip values to [0,1] since the collaboration boost/discount can push coverage over 1.0 and under 0
    df['average'] =  df['average'].clip(lower=0.0, upper=1.0)
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
                width=width, height=height )
    applyStandardVBarFormatting(fig)

    return po.to_html(fig, include_plotlyjs='cdn', full_html=True)

def facingCapsDataGraphByCC(answers, facing, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    return '<br><h3 class="graphNYI">This graph is Not Yet Implemented</h3>'

def capsDataGraphByMission(answers, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    return '<br><h3 class="graphNYI">This graph is Not Yet Implemented</h3>'

def facingCapsDataGraphByMission(answers, facing, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    return '<br><h3 class="graphNYI">This graph is Not Yet Implemented</h3>'

def capsDataGraphByPubPriv(answers, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    #print("capsDataGraphByCC with: ", answers.count()," answers")
    if (answers.count() == 0): 
        return None
    answers = answers.filter(assessment__profile__institution__ipeds_control__isnull=False)
    data = answers.aggregate_score('question__topic__facing','assessment__profile__institution__ipeds_control'). \
        values('question__topic__facing','assessment__profile__institution__ipeds_control','average','stddev')

    df= pd.DataFrame(data)
    df['question__topic__facing'] = df['question__topic__facing'].map(Facing_mapping) # Map the classification values to names
    # print("Private-Public Data \n", df)

    # Map the values to names
    df['assessment__profile__institution__ipeds_control'] =  df['assessment__profile__institution__ipeds_control'].map(pubpriv_mapping)
    # clip values to [0,1] since the collaboration boost/discount can push coverage over 1.0 and under 0
    df['average'] =  df['average'].clip(lower=0.0, upper=1.0)
    # Multiply by 100 to display percentages
    df['average'] *= 100
    df['stddev'] *= 100

    # Rename the columns for clarity
    df =  df.rename(columns={
            'question__topic__facing' : 'Facings',
            'assessment__profile__institution__ipeds_control' :'Public/Private',
            'average':'Average Values',
        })

    # Create a grouped bar chart
    fig = px.bar( df, x='Facings', y='Average Values',error_y='stddev',
                    barmode='group',  # Use 'group' for grouped bars
                    color='Public/Private',
                    color_discrete_map={'Public': colorPalette['Public'], 'Private': colorPalette['Private']},  # Set custom color
                    labels={'Facings': 'Facings', 'value': 'Average Values'},
                    width=800, height=600)
    applyStandardVBarFormatting(fig)

    # Convert the figure to HTML including Plotly.js
    return po.to_html(fig, include_plotlyjs='cdn', full_html=True)

def facingCapsDataGraphByPubPriv(answers, facing, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    return '<br><h3 class="graphNYI">This graph is Not Yet Implemented</h3>'

def capsDataGraphByEPSCoR(answers, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    #print("capsDataGraphByEPSCoR with: ", answers.count()," answers")
    if (answers.count() == 0): 
        return None
    answers = answers.filter(assessment__profile__institution__ipeds_epscor__isnull=False)
    data = answers.aggregate_score('question__topic__facing','assessment__profile__institution__ipeds_epscor'). \
        values('question__topic__facing','assessment__profile__institution__ipeds_epscor','average','stddev')

    df= pd.DataFrame(data)
    df['question__topic__facing'] = df['question__topic__facing'].map(Facing_mapping) # Map the classification values to names
    # print("EPSCoR Data \n", df)

    # Map the values to names
    df['assessment__profile__institution__ipeds_epscor'] =  df['assessment__profile__institution__ipeds_epscor'].map(epscor_mapping)
    # clip values to [0,1] since the collaboration boost/discount can push coverage over 1.0 and under 0
    df['average'] =  df['average'].clip(lower=0.0, upper=1.0)
    # Multiply by 100 to display percentages
    df['average'] *= 100
    df['stddev'] *= 100

    # Rename the columns for clarity
    df =  df.rename(columns={
            'question__topic__facing' : 'Facings',
            'assessment__profile__institution__ipeds_epscor' :'EPSCoR',
            'average':'Average Values',
        })

    # Create a grouped bar chart
    fig = px.bar( df, x='Facings', y='Average Values',error_y='stddev',
                    barmode='group',  # Use 'group' for grouped bars
                    color='EPSCoR',
                    color_discrete_map={Institution.EPSCORChoices.EPSCOR.label: colorPalette['EPSCoR'], 
                                        Institution.EPSCORChoices.NOT_EPSCOR.label: colorPalette['nonEPSCoR']},  # Set custom color
                    labels={'Facings': 'Facings', 'value': 'Average Values'},
                    width=800, height=600)
    applyStandardVBarFormatting(fig)

    # Convert the figure to HTML including Plotly.js
    return po.to_html(fig, include_plotlyjs='cdn', full_html=True)

def facingCapsDataGraphByEPSCoR(answers, facing, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    return '<br><h3 class="graphNYI">This graph is Not Yet Implemented</h3>'

def capsDataGraphByMSI(answers, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    return '<br><h3 class="graphNYI">This graph is Not Yet Implemented</h3>'

def facingCapsDataGraphByMSI(answers, facing, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    return '<br><h3 class="graphNYI">This graph is Not Yet Implemented</h3>'

def capsDataGraphByOrgModel(answers, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    # Org Model is call "structure" in the model - not very useful until we have more metadata. Sigh. 
    print("capsDataGraphByOrgModel with: ", answers.count()," answers")
    if (answers.count() == 0): 
        return None
    answers = answers.filter(assessment__profile__structure__isnull=False)
    instCount = answers.values('assessment__id').distinct().count()
    print("capsDataGraphByOrgModel filtering for Nulls: ", instCount," Institutions")
    data = answers.aggregate_score('question__topic__facing','assessment__profile__structure'). \
        values('question__topic__facing','assessment__profile__structure','average','stddev')

    df= pd.DataFrame(data)
    df['question__topic__facing'] = df['question__topic__facing'].map(Facing_mapping) # Map the classification values to names
    # print("OrgModel Data \n", df)

    # Map the values to names
    df['assessment__profile__structure'] =  df['assessment__profile__structure'].map(structure_mapping)
    # clip values to [0,1] since the collaboration boost/discount can push coverage over 1.0 and under 0
    df['average'] =  df['average'].clip(lower=0.0, upper=1.0)
    # Multiply by 100 to display percentages
    df['average'] *= 100
    df['stddev'] *= 100

    # Rename the columns for clarity
    df =  df.rename(columns={
            'question__topic__facing' : 'Facings',
            'assessment__profile__structure' :'OrgModel',
            'average':'Average Values',
        })

    # Create a grouped bar chart
    fig = px.bar( df, x='Facings', y='Average Values',error_y='stddev',
                    barmode='group',  # Use 'group' for grouped bars
                    color='OrgModel',
                    color_discrete_map={'Centralized': colorPalette['Centralized'], 
                                        'In a School/Dept.': colorPalette['School'], 
                                        'Decentralized across units': colorPalette['Decentralized'], 
                                        'No organized support': colorPalette['None'], 
                                        },  # Set custom color
                    labels={'Facings': 'Facings', 'value': 'Average Values'},
                    width=800, height=600)
    applyStandardVBarFormatting(fig)

    # Convert the figure to HTML including Plotly.js
    return po.to_html(fig, include_plotlyjs='cdn', full_html=True)

def facingCapsDataGraphByOrgModel(answers, facing, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    return '<br><h3 class="graphNYI">This graph is Not Yet Implemented</h3>'

def capsDataGraphByReporting(answers, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    return '<br><h3 class="graphNYI">This graph is Not Yet Implemented</h3>'

def facingCapsDataGraphByReporting(answers, facing, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    return '<br><h3 class="graphNYI">This graph is Not Yet Implemented</h3>'

