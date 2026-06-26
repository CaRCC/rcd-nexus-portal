# from django.shortcuts import render
import re
import textwrap
from django.db.models import Q, Case, Value, When, F, Count
from functools import reduce
from operator import or_
from math import ceil
from nexus.models import CapabilitiesQuestion, CapabilitiesAnswer, CapabilitiesAssessment, CapabilitiesTopic, Institution, RCDProfile
from nexus.forms import dataviz
#from django.http import JsonResponse
import colorsys
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as po
from django.db.models import Q

DEFAULT_WIDTH = 800
DEFAULT_HEIGHT = 600
GRAPHSIZE_MED_SCALE = 0.8       # 640 X 420
GRAPHSIZE_SMALL_SCALE = 0.6     # 480 X 360
CALCULATE_SCALED_HEIGHT = -1
MAX_TOPICS = 11         # Systems has the most
MARKER_SZ = 25

INCLUDE_PLOTLYJS = 'cdn'  #REVERT THIS TO 'cdn' for checkin - Use True ONLY FOR OFFLINE!!

VALUE_UNKNOWN = "unknown"
VALUE_UNKNOWN_LABEL = "Unknown"

barmarkercolors = ['darkorchid', 'orchid', 'plum']
vbarmarkertypes = ['diamond-wide-dot', 'hexagon2-dot', 'circle-dot']
hbarmarkertypes = ['diamond-tall-dot', 'hexagon-dot', 'circle-dot']
barmarkerscales = [1, .9, .75]
NMARKERSMAX = 3

colorPalette = {'allData':'#9F9F9F', 'EPSCoR':'#5ab4ac', 'nonEPSCoR':'#d8b365', 
                'errBars':'#bbb', 'lightErrBars':'#f5f5f5', 'bgColor':'#555',
                'RF':'#40bad2', 'DF': '#fab900', 'SWF':'#a147a8', 'SYF':'#ee7008', 'SPF':'#D81B60',
                'R1':'#2e75b6','R2':'#8bb8e1','R3':'#d1e3f3','AllButR1':'#d1e3f3','OtherAcad':'#d1e3f3','Other':'#e9f0f7',
                'M1':'#95A472','M2':'#C8E087','M3':'#DDFCAD','Bacc':'#F7EF81',
                'Centralized':'#A37C40','School':'#98473E','Decentralized':'#B49082','None':'#D6C3C9',
                'Public':'#ffd966','Private':'#ec7728',
                'MSI':'#0084d1', 'NotMSI':'#8FB8DE','HSI':'#586F6B','HBCU':'#CFE795','AA':'#F7EF81','TCU':'#D4C685','otherMSI':'#D0CFEC',
                VALUE_UNKNOWN_LABEL:'#8d99ae',
                '2022':'#ffba5a', '2021':'#6aaa96', '2020':'#ada3d3',
                'defaultLegendFontColor':'#000', 'noDataLegendFontColor':'#9F9F9F',}

def hex_to_rgb(h):
    h = h.lstrip('#')
    return [int(h[i:i+2], 16) for i in (0, 2, 4)]

def adjust_color_lightness(hex, factor):
    r,g,b = hex_to_rgb(hex)
    h, l, s = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
    l = max(min(l * factor, 1.0), 0.0)
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    lighter = '#%02x%02x%02x' % (int(r * 255), int(g * 255), int(b * 255))
    #print('adjust_color_lightness(',hex,', ', factor, '): ', lighter)
    return lighter

def lighten_color(hex, factor=0.1):
    return adjust_color_lightness(hex, 1+factor)

def darken_color(hex, factor=0.1):
    return adjust_color_lightness(hex, 1-factor)


scatterPlotcolorMap = {'RT':colorPalette['RF'],'DT':colorPalette['DF'], 'SWT':colorPalette['SWF'],
                                    'SYT':colorPalette['SYF'], 'SPT':colorPalette['SPF']}
scatterPlotColorSeq = [colorPalette['RF'],colorPalette['DF'],colorPalette['SWF'],colorPalette['SYF'],colorPalette['SPF']]

# QUESTION Why does this work?  Facings fixture defines the indices as 0-4, not 1-5
Facing_mapping = { 1: '<b>Researcher-<br>Facing</b>', 2: '<b>Data-<br>Facing</b>', 3: '<b>Software-<br>Facing</b>', 4 : '<b>System-<br>Facing</b>', 5: '<b>Strategy & Policy-<br>Facing</b>'}
Facing_xvals = list(Facing_mapping.values())

colorSeqForFacings = [lighten_color(colorPalette['RF'],.4), lighten_color(colorPalette['DF'],.4),
                      lighten_color(colorPalette['SWF'],.4),lighten_color(colorPalette['SYF'],.4),
                      lighten_color(colorPalette['SPF'],.4)]
colorMapByFacingSlug = {'researcher':colorSeqForFacings[0],'data':colorSeqForFacings[1],'software':colorSeqForFacings[2],
                        'systems':colorSeqForFacings[3],'strategy':colorSeqForFacings[4]}
#print(colorSeqForFacings)

RFLabels = {'staffing':'<b>RCD Staffing  </b>',
            'outreach':'<b>RCD Outreach  </b>',
            'consulting':'<b>RCD Adv. Support  </b>',
            'lifecycle':'<b>Research  <br>Lifecycle Mgmnt  </b>'}
RFLabels_yvals = list(RFLabels.values())

DFLabels = {'creation':'<b>Data Creation  </b>',
            'discovery': '<b>Data Discovery  <br>& Collection  </b>',
            'analysis':'<b>Data Analysis  </b>',
            'visualization':'<b>Data Visualization  </b>',
            'curation':'<b>Curation  </b>',
            'policy':'<b>Data Policy  <br>Compliance  </b>',
            'security':'<b>Security/Sensitive Data  </b>'}
DFLabels_yvals = list(DFLabels.values())

SWFLabels = {'management':'<b>SW Package Mgmnt  </b>',
             'development':'<b>Research SW  <br>Development  </b>',
             'optimization':'<b>SW Optimization,  <br>Troubleshooting  </b>',
             'workflow':'<b>Workflow Engineering  </b>',
             'portability':'<b>SW Portability,  <br>Containers, Cloud  </b>',
             'access':'<b>Securing Access to SW  </b>',
             'physical_specimens':'<b>SW for Physical  <br>Specimen Mgmnt  </b>'}
SWFLabels_yvals = list(SWFLabels.values())

SYFLabels = {'infrastructure':'<b>Infrastructure Support  </b>',
             'compute':'<b>Compute Infrastructure  </b>',
             'storage':'<b>Storage Infrastructure  </b>',
             'network':'<b>Network and Data  <br>Movement  </b>',
             'specialized':'<b>Specialized Infrastructure  </b>',
             'software':'<b>Infrastructure Software  </b>',
             'monitoring': '<b>Monitoring and  <br>Measurement  </b>',
             'recordkeeping':'<b>Change Mgmnt,  <br>Version Control, etc.  </b>',
             'documentation':'<b>Documentation </b>',
             'planning':'<b>Planning  </b>',
             'security':'<b>Security Practices  <br>for Open Environments  </b>'}
SYFLabels_yvals = list(SYFLabels.values())

SPFLabels = {'alignment':'<b>Institutional Alignment  </b>',
             'culture':'<b>Institutional Culture  <br>for Research Support  </b>',
             'funding':'<b>Funding  </b>',
             'partnerships':'<b>Partnerships &  <br>External Engagement  </b>',
             'professionalization':'<b>RCD Professional  <br>Development  </b>',
             'diversity':'<b>Diversity, Equity,  <br>and Inclusion  </b>'}
SPFLabels_yvals = list(SPFLabels.values())


# SimpleCC values - ordered for presentation
CC_BACC = 97
CC_TCU = 98
CC_OTHERACAD = 99
CC_OTHER = 100
CC_INDUSTRY = 101
CC_MISC = 102
CC_UNKNOWN = 999

def initCCMapping():
    mapping = {}
    mapping[CC_BACC] = 'Bacc'
    mapping[CC_TCU] = 'TCU'
    mapping[CC_OTHERACAD] = 'Other Acad.'
    mapping[CC_OTHER] = Institution.CarnegieClassificationChoices.OTHER.label
    mapping[CC_MISC] = Institution.CarnegieClassificationChoices.MISC.label
    mapping[CC_INDUSTRY] = Institution.CarnegieClassificationChoices.INDUSTRY.label
    mapping[CC_UNKNOWN] = 'Unknown'
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

# Define a dictionary to map Structure values to names
reporting_mapping = {
    RCDProfile.OrgChartChoices.INFOTECH: "IT (e.g., CIO)",
    RCDProfile.OrgChartChoices.RESEARCH: "Research (e.g., VPR)",
    RCDProfile.OrgChartChoices.ACADEMIA: "Academic leadership<br>(e.g., Provost or a Dean)",
    RCDProfile.OrgChartChoices.INSTITUTE: "Academic/Research<br>Institute or Center",
    RCDProfile.OrgChartChoices.OTHER: RCDProfile.OrgChartChoices.OTHER.label,
    VALUE_UNKNOWN: VALUE_UNKNOWN_LABEL
    }

reporting_palette = {
    "IT (e.g., CIO)":'#dda15e',
    "Research (e.g., VPR)":'#fefae0',
    "Academic leadership<br>(e.g., Provost or a Dean)":'#283618',
    "Academic/Research<br>Institute or Center": '#606c38',
    RCDProfile.OrgChartChoices.OTHER.label: '#f0f0f0',
    VALUE_UNKNOWN_LABEL:colorPalette[VALUE_UNKNOWN_LABEL]
    }



def computeMaxRange(averages, stddevs):
    if averages.empty or stddevs.empty :
        maxRange = 100
    else:
        maxRange = max(averages)+max(stddevs)
        maxRange = min(100, max(7, int((maxRange+.05)*10))*10)
    return maxRange

def getAllAnswers(years=None, excludeDemos=True) :
    # Restrict to approved assessments
    profiles = RCDProfile.objects.filter(capabilities_assessment__review_status=CapabilitiesAssessment.ReviewStatusChoices.APPROVED)
    if excludeDemos:
        profiles = profiles.exclude(institution__id__in=Institution.getDemoIDList())
    if not years is None:
        # print('getAllAnswers filtering to years: ',years)
        profiles = profiles.filter(year__in=years)
    # Now ensure we only have the latest profile for each institution for the given set of years
    profiles = profiles.order_by('institution', '-year').distinct('institution')
    #print("getAllAnswers found: ",profiles.count()," distinct non-superseded profiles")
    answers = CapabilitiesAnswer.objects.filter(assessment__profile__in=profiles)
    # Get only the main answers (skip the domain coverage ones)
    answers = answers.filter(not_applicable=False).exclude(question__topic__slug=CapabilitiesTopic.domain_coverage_slug)
    #print(answers.count())
    instCount = answers.values('assessment__id').distinct().count()

    return answers, instCount

# Translate URL query parameters into a filter for CapabilitiesAnswer objects
# Note that we skip filtering when all values are chosen. This is both more efficient, and moreover
# ensures that we do not filter out all the Null values (e.g., for mission) on older profiles. 
def filterAssessmentData(dict, bmQuestions=None):

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

    if resexp_min := dict.get('resexp_min'):
        minMills = int(resexp_min)
        if minMills > 0:
            answers = answers.filter(assessment__profile__institution__research_expenditure__gte=(minMills*1000000))
    if resexp_max := dict.get('resexp_max'):
        maxMills = int(resexp_max)
        if maxMills > 0:
            answers = answers.filter(assessment__profile__institution__research_expenditure__lte=(maxMills*1000000))
 
    if bmQuestions != None:
        #print('filterAssessmentData has bmQuestions; before filtering with that # Qs is:'+str(answers.values('question__id').distinct().count()))
        answers = answers.filter(question__id__in=bmQuestions)
        #print('after  filtering with that # Qs is:'+str(answers.values('question__id').distinct().count()))

    instCount = answers.values('assessment__id').distinct().count()
    #print("After filtering have: ",answers.count(), " answers for: ",instCount," Institutions")

    return answers, instCount

def applyStandardVBarFormatting(fig, width=None, textscale=1, nCats=0):
    # Apply standard font size and font type
    fig.update_layout(
        xaxis=dict(title=dict(text='', font=dict(size=16, family='Arial'))),
        yaxis=dict(title=dict(text='', font=dict(size=16, family='Arial')), ticksuffix="%", range=[0, 100], dtick=20),
        plot_bgcolor=colorPalette['bgColor'], 
        margin_t=25,autosize=True,
        legend_title_text='',
        #legend_traceorder="normal",
        legend = dict(font=dict(size=14*textscale, )),
        )
    if(nCats<4):
        error_w = 3*textscale 
        error_t = 2*textscale
    else: # For busy graphs that are small, further reduce the error bar cap width
        error_w = 3*textscale*textscale 
        error_t = 2*textscale*textscale
    
    fig.update_traces(error_y=dict(color=colorPalette['errBars'],width=error_w, thickness=error_t),
                      marker_line_color='black', marker_line_width=1.5,width=width, hovertemplate = 'Coverage: %{y:.1f}%',
                      showlegend=True)
    fig.update_yaxes(gridcolor=colorPalette['errBars'], gridwidth=0.5, griddash='dot',zeroline=False)

def applyStandardHBarFormatting(fig, width=None, textscale=1, nCats=0):
    # Apply standard font size and font type
    fig.update_layout(
        yaxis=dict(title=dict(text='')), #, font=dict(size=16, family='Arial'))),
        xaxis=dict(title=dict(text='', font=dict(size=16, family='Arial')), ticksuffix="%", range=[0, 100], dtick=20),
        plot_bgcolor=colorPalette['bgColor'], 
        # margin_t=25, margin_l=20,
        margin=dict(l=20, r=0, t=25, b=0),
        autosize=True,
        legend_title_text='',        
        bargap=0.250,
        legend = dict(font=dict(size=14*textscale, )),
        )
    if(nCats<4):
        error_w = 3*textscale 
        error_t = 2*textscale
    else: # For busy graphs that are small, further reduce the error bar cap width
        error_w = 3*textscale*textscale 
        error_t = 2*textscale*textscale
    fig.update_traces(error_x=dict(color=colorPalette['errBars'],width=error_w, thickness=error_t),
                  marker_line_color='black', marker_line_width=1.5,width=width, hovertemplate = 'Coverage: %{x:.1f}%')
    fig.update_yaxes(showgrid=False,zeroline=False, autorange="reversed",
                     showline=True, linewidth=1, linecolor='black',
                     tickfont=dict(size=14*textscale, family='Arial'),)
    fig.update_xaxes(gridcolor=colorPalette['errBars'], gridwidth=0.5, griddash='dot', zeroline=False)


def allSummaryDataGraph(width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    answers, instCount = getAllAnswers()
    return summaryDataGraph(answers, width=width, height=height), instCount

def summaryDataGraph(answers, benchmarks=None, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT, showErrBars=True):
    #print("SummaryDataGraph with: ", answers.count()," answers")
    #instCount = answers.values('assessment__id').distinct().count()
    #print("SummaryDataGraph with: ", answers.count()," answers for: ",instCount," Institutions")
    if (answers.count() == 0): 
        return None

    #Note that answers has been pre-filtered of domain topic and not_applicable answers
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
    #print(data)

    # Compute a naive graph max and consider limiting the y axis (there is no simple way to compute the max of the sum) 
    # No - this is making the graphs jitter for comparison. 
    maxYRange = 100 #computeMaxRange(data['Average Values'], data['Std Dev'])
    # print("MaxYRange: "+str(maxYRange))

    data['Average Values'] *= 100
    data['Std Dev'] *= 100

    markerscale = 1.3-((1-(abs(height)/DEFAULT_HEIGHT))*1.4)
    textscale = 1-((1.3-markerscale)*.4)
    # Create a All Summary Data bar chart
    fig = px.bar(data, x='Facings', y= 'Average Values', error_y='Std Dev' if showErrBars else None,
                    #width=width, height=height,color_discrete_sequence=[colorPalette['allData']]*5)
                    width=width, height=height,color='Facings', color_discrete_sequence=colorSeqForFacings)
    applyStandardVBarFormatting(fig, width=0.6, textscale=textscale)
    fig.update_traces(showlegend=False) # For the summary data graph, the facings are labeled on the X axis, so redundant in the legend. 

    # If benchmark data passed in, layer that over
    # Note that at the top level, there will be no benchmarks with no data
    if(benchmarks!=None) :
        # We add them in reverse order so the most recent is on top
        # Legendrank is SUPPOSED to let us order with the most recent year on top, but seems not to work.
        imarker = min(len(benchmarks), NMARKERSMAX)-1
        while imarker >= 0:
            bm = benchmarks[imarker]
            fig.add_trace(go.Scatter(x=Facing_xvals, y=bm['data'], mode='markers', 
                                        marker_color=barmarkercolors[imarker], marker_line_width=2, marker_line_color='white',
                                        marker_size=MARKER_SZ*markerscale*barmarkerscales[imarker], marker_symbol=vbarmarkertypes[imarker], name=bm['name'],
                                        legendrank=(5-imarker)))
            imarker-=1
        fig.update_traces(hovertemplate = 'Coverage: %{y:.1f}%<extra></extra>')
        fig.update_layout(showlegend=True)
   
    # Convert the figure to HTML including Plotly.js
    return po.to_html(fig, include_plotlyjs=INCLUDE_PLOTLYJS, full_html=True)

def labelForFacingTopic(facing, topic):
    # print(f'labelForFacingTopic({facing},{topic})')
    map = labelMapForFacing(facing)[0]
    rex_spaces = re.compile(r'\s+')
    rex_tags = re.compile(r'<[^<]+?>')
    return rex_spaces.sub(' ', rex_tags.sub('', map[topic])).strip()


def labelMapForFacing(facing):
    match facing:
        case "researcher":
            return RFLabels, RFLabels_yvals
        case "data":
            return DFLabels, DFLabels_yvals
        case "software":
            return SWFLabels, SWFLabels_yvals
        case "systems":
            return SYFLabels, SYFLabels_yvals
        case "strategy":
            return SPFLabels, SPFLabels_yvals
        case _ :
            raise ValueError(f"labelMapForFacing: unrecognized facing: {facing}")

def midsplit(stringToSplit, linemax, splitReplace='<br>'):
    inputLen = len(stringToSplit)
    if inputLen <= linemax:
        return stringToSplit
    # Split as close to the midpoint as possible, preferring a longer first line than second
    midpoint = int(inputLen/2)
    splitPoint = 0
    if stringToSplit[midpoint] == ' ': # can skip the rest if evenly splits at midpoint
        splitPoint = midpoint
    else:
        for i in range(1, midpoint-1):
            if stringToSplit[midpoint+i] == ' ':
                splitPoint = midpoint+i
                break
            if stringToSplit[midpoint-i] == ' ':
                splitPoint = midpoint-i
                break

    if splitPoint == 0:
        print(f'midsplit could not find a place to split string: [{stringToSplit}]')
        return stringToSplit
    
    return stringToSplit[0:splitPoint] + splitReplace + stringToSplit[splitPoint+1:]

def labelMapForTopic(facingSlug, topicSlug):
    # We build a quick dictionary from the Question data and return that along with the values (for axis labels)
    # If the string length is under 24, leave as is. Else, find the word break closest to the center of the string and replace with a <br> tag
    questions = CapabilitiesQuestion.objects.filter_valid().filter(topic__facing__slug=facingSlug).filter(topic__slug=topicSlug).order_by('index')
    qdict = dict((q.slug, f'<b>{midsplit(q.contents.get(language="en").shorttext, 22)}</b>') for q in questions)
    return qdict, list(qdict.values())


# Scale the height, accounting for the number of categories on the y axis, as well as the number of items in the legend
def calculateScaledHeight(nCats, nLegendItems, height, lowCountAdj=.5):
    if nCats >= nLegendItems:
        yCount = nCats
    else:
        yCount = nCats + min((nLegendItems-nCats)/2, 2)
    scale = yCount/MAX_TOPICS
    adjustedscale = 1 - ((1-scale)*.5)     # scale by a fraction of the difference in # of Topics
    scaledHeight = adjustedscale*height
    if yCount < 6:
        # We have 2 sub-cats, so scale the height for topics with few questions, unless we are rendering smaller graphs
        scaledHeight = scaledHeight*(lowCountAdj+(1-lowCountAdj)*(yCount/6))
    # print(f'calculateScaledHeight({nCats},{nLegendItems},{height},{lowCountAdj}): {scaledHeight}')
    return scaledHeight


def facingSummaryDataGraph(answers, facing, benchmarks=None,
                           width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT, showErrBars=True):
    #print(f"Facing: [{facing}] SummaryDataGraph with: {answers.count()} answers")
    #instCount = answers.values('assessment__id').distinct().count()
    if (answers.count() == 0): 
        return None
    
    #Note that answers has been pre-filtered of domain topic and not_applicable answers
    data = answers.aggregate_score('question__topic__slug')\
        .values('question__topic__slug','average','stddev')\
        .filter(question__topic__facing__slug=facing).order_by('question__topic__index')

    # Convert the queryset to a DataFrame
    df = pd.DataFrame(data)
    # print(f'facingSummaryDataGraph DF: {df}')

    # Map the topic slugs to names
    labelMap, yvalues = labelMapForFacing(facing)

    df['question__topic__slug'] = df['question__topic__slug'].map(labelMap)
    data = df

    # Rename the columns for clarity
    data = data.rename(columns={
            'average':'Average Values',
            'question__topic__slug' : 'Topics',
            'stddev' : 'Std Dev'
        })
    # print(data)

    data['Average Values'] *= 100
    data['Std Dev'] *= 100

    markerscale = 1-((1-(abs(height)/DEFAULT_HEIGHT))*1.3)
    textscale = 0.9-((1-markerscale)*.3)

    if height <= CALCULATE_SCALED_HEIGHT:
        height = calculateScaledHeight(len(yvalues), 0, abs(height))

    # Create a Topics Summary Data bar chart for this facing
    fig = px.bar(data, y='Topics', x= 'Average Values', error_x='Std Dev' if showErrBars else None,
                    width=width, height=height,color_discrete_sequence=[colorPalette['allData']]*5)
    fig.update_traces(marker_color=colorMapByFacingSlug[facing])
    applyStandardHBarFormatting(fig, width=0.6, textscale=textscale)

    # If benchmark data passed in, layer that over
    if(benchmarks!=None) :
        # We add them in reverse order so the most recent is on top
        imarker = min(len(benchmarks), NMARKERSMAX)-1
        while imarker >= 0:
            bm = benchmarks[imarker]
            if bm['hasData']:
                bmName = bm['name']
            else:
                bmName = '<span style="font-style:italic;fill:'+colorPalette['noDataLegendFontColor']+';">'+bm['name']+'</em>'
            fig.add_trace(go.Scatter(y=yvalues, x=bm['data'], mode='markers', 
                                        marker_color=barmarkercolors[imarker], marker_line_width=2, marker_line_color='white',
                                        marker_size=MARKER_SZ*markerscale*barmarkerscales[imarker], marker_symbol=hbarmarkertypes[imarker], 
                                        name=bmName))
            imarker-=1
        fig.update_traces(hovertemplate = 'Coverage: %{x:.1f}%<extra></extra>')
   
    # Convert the figure to HTML including Plotly.js
    return po.to_html(fig, include_plotlyjs=INCLUDE_PLOTLYJS, full_html=True)

def topicSummaryDataGraph(answers, facing, topic, benchmarks=None,
                           width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT, showErrBars=True):
    #print(f"Facing/Topic: [{facing}/{topic}] SummaryDataGraph with: {answers.count()} answers")
    #instCount = answers.values('assessment__id').distinct().count()
    if (answers.count() == 0): 
        return None
    
    #Note that answers has been pre-filtered of domain topic and not_applicable answers
    # Note also that the topic sligs are unique so we skip filtering on the facing
    data = answers.aggregate_score('question__slug')\
        .values('question__slug','average','stddev')\
        .filter(question__topic__facing__slug=facing)\
        .filter(question__topic__slug=topic).order_by('question__index')

    # Convert the queryset to a DataFrame
    df = pd.DataFrame(data)
    # print(f'topicSummaryDataGraph DF: {df}')

    # Map the question slugs to their short names
    labelMap, yvalues = labelMapForTopic(facing, topic)

    df['question__slug'] = df['question__slug'].map(labelMap)
    data = df

    # Rename the columns for clarity
    data = data.rename(columns={
            'average':'Average Values',
            'question__slug' : 'Questions',
            'stddev' : 'Std Dev'
        })
    # print(data)

    data['Average Values'] *= 100
    data['Std Dev'] *= 100

    markerscale = 1-((1-(abs(height)/DEFAULT_HEIGHT))*1.3)
    textscale = 0.9-((1-markerscale)*.3)

    if height <= CALCULATE_SCALED_HEIGHT:
        legendCount = 0
        if(benchmarks!=None):
            legendCount = legendCount+len(benchmarks)
        height = calculateScaledHeight(len(yvalues), legendCount, abs(height))

    # Create a Topics Summary Data bar chart for this facing
    fig = px.bar(data, y='Questions', x= 'Average Values', error_x='Std Dev' if showErrBars else None,
                    width=width, height=height,color_discrete_sequence=[colorPalette['allData']]*5)
    fig.update_traces(marker_color=colorMapByFacingSlug[facing])
    applyStandardHBarFormatting(fig, width=0.6, textscale=textscale)

    # If benchmark data passed in, layer that over
    if(benchmarks!=None) :
        # We add them in reverse order so the most recent is on top
        imarker = min(len(benchmarks), NMARKERSMAX)-1
        while imarker >= 0:
            bm = benchmarks[imarker]
            if bm['hasData']:
                bmName = bm['name']
            else:
                bmName = '<span style="font-style:italic;fill:'+colorPalette['noDataLegendFontColor']+';">'+bm['name']+'</em>'
            # print(f'topicSummaryDataGraph adding bm: {bm} for yvalues: {yvalues}')
            print(f'topicSummaryDataGraph bmName: "{bmName}"')
            fig.add_trace(go.Scatter(y=yvalues, x=bm['data'], mode='markers', 
                                        marker_color=barmarkercolors[imarker], marker_line_width=2, marker_line_color='white',
                                        marker_size=MARKER_SZ*markerscale*barmarkerscales[imarker], marker_symbol=hbarmarkertypes[imarker], 
                                        name=bmName))
            imarker-=1
        fig.update_traces(hovertemplate = 'Coverage: %{x:.1f}%<extra></extra>')
   
    # Convert the figure to HTML including Plotly.js
    return po.to_html(fig, include_plotlyjs=INCLUDE_PLOTLYJS, full_html=True)

def capsDataGraphByCC(answers, benchmarks=None, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT, showErrBars=True):
    #print("capsDataGraphByCC with: ", answers.count()," answers")
    if (answers.count() == 0): 
        return None
    # For this graph, we will ignore the "Other" institutions (labs, etc.), the Unknowns which have Null values for CC, and 
    # anything in our extended definitions (MISC, INDUSTRY, etc.)
    # If we get many more contributions from these groups, we can reconsider
    answers = answers.filter(Q(assessment__profile__institution__carnegie_classification__isnull=False)
                           | Q(assessment__profile__institution__carnegie_classification=Institution.CarnegieClassificationChoices.OTHER)
                           | Q(assessment__profile__institution__carnegie_classification__gte=Institution.CarnegieClassificationChoices.MISC)
                            )
    annotatedAnswers = answers.annotate(simpleCC=Case(
        When(assessment__profile__institution__carnegie_classification=15, then=Value(15)),
        When(assessment__profile__institution__carnegie_classification=16, then=Value(16)),
        default=Value(CC_OTHERACAD) ))
    
    # instCount = answers.values('assessment__id').distinct().count()
    # Need to count distinct institutions in answers grouped by simpleCC
    # simpleCCValueCounts = annotatedAnswers.values('simpleCC').annotate(count=Count('simpleCC'))
    # print('simpleCCValueCounts: ', simpleCCValueCounts)

    # Note that answers has been pre-filtered of domain topic and not_applicable answers
    data = annotatedAnswers.aggregate_score('question__topic__facing','simpleCC').values('question__topic__facing','simpleCC','average','stddev')
    df = pd.DataFrame(data)     # Convert the queryset to a DataFrame
    # Map the facings values to names
    df['question__topic__facing'] = df['question__topic__facing'].map(Facing_mapping)
    df['simpleCC'] = df['simpleCC'].map(cc_mapping)

    # print('Filtered data has ', df['simpleCC'].nunique(),' of 3 expected CC values')
    missing_cats = True if df['simpleCC'].nunique() < 3 else False

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

    markerscale = 1.3-((1-(abs(height)/DEFAULT_HEIGHT))*1.4)
    textscale = 1-((1.3-markerscale)*.4)
    # Create a grouped bar chart
    fig = px.bar(df, x='Facings', y='Average Value',error_y='stddev' if showErrBars else None,
                color='simpleCC', 
                color_discrete_map={'R1':colorPalette['R1'], 'R2':colorPalette['R2'],'Other Acad.':colorPalette['OtherAcad']},
                barmode='group', # Use 'group' for grouped bars
                width=width, height=height )
    applyStandardVBarFormatting(fig, textscale=textscale)

    # If benchmark data passed in, layer that over
    # At the top level, no benchmark will be empty, even if it has no data for some facing
    if(benchmarks!=None) :
        # We add them in reverse order so the most recent is on top
        imarker = min(len(benchmarks), NMARKERSMAX)-1
        while imarker >= 0:
            bm = benchmarks[imarker]
            fig.add_trace(go.Scatter(x=Facing_xvals, y=bm['data'], mode='markers', 
                                        marker_color=barmarkercolors[imarker], marker_line_width=2, marker_line_color='white',
                                        marker_size=MARKER_SZ*markerscale*barmarkerscales[imarker], marker_symbol=vbarmarkertypes[imarker], name=bm['name']))
            imarker-=1
        fig.update_traces(hovertemplate = 'Coverage: %{y:.1f}%<extra></extra>')

    return po.to_html(fig, include_plotlyjs=INCLUDE_PLOTLYJS, full_html=True), missing_cats

def facingCapsDataGraphByCC(answers, facing, topic, benchmarks=None, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT, showErrBars=True):
    #print(f'facingCapsDataGraphByCC({facing},{topic}) with: {answers.count()} answers')
    if (answers.count() == 0): 
        return None
    # For this graph, we will ignore the "Other" institutions (labs, etc.), the Unknowns which have Null values for CC, and 
    # anything in our extended definitions (MISC, INDUSTRY, etc.)
    # If we get many more contributions from these groups, we can reconsider
    answers = answers.filter(Q(assessment__profile__institution__carnegie_classification__isnull=False)
                           | Q(assessment__profile__institution__carnegie_classification=Institution.CarnegieClassificationChoices.OTHER)
                           | Q(assessment__profile__institution__carnegie_classification__gte=Institution.CarnegieClassificationChoices.MISC)
                            )
    answers = answers.filter(question__topic__facing__slug=facing)
    if topic != 'all':
        answers = answers.filter(question__topic__slug=topic)
    
    annotatedAnswers = answers.annotate(simpleCC=Case(
        When(assessment__profile__institution__carnegie_classification=15, then=Value(15)),
        When(assessment__profile__institution__carnegie_classification=16, then=Value(16)),
        default=Value(CC_OTHERACAD) ))

    # Note that answers has been pre-filtered of domain topic and not_applicable answers
    if topic == 'all':
        annotatedAnswers = annotatedAnswers.order_by('question__topic__index', 'simpleCC')
        data = annotatedAnswers.aggregate_score('question__topic__slug','simpleCC')\
            .values('question__topic__slug','simpleCC','average','stddev')
        # Map the topic slugs to names
        labelMap, yvalues = labelMapForFacing(facing)
        df = pd.DataFrame(data)     # Convert the queryset to a DataFrame
        df['question__topic__slug'] = df['question__topic__slug'].map(labelMap)
    else:
        annotatedAnswers = annotatedAnswers.order_by('question__index', 'simpleCC')
        data = annotatedAnswers.aggregate_score('question__slug','simpleCC')\
            .values('question__slug','simpleCC','average','stddev')
        # Map the question slugs to names
        labelMap, yvalues = labelMapForTopic(facing, topic)
        df = pd.DataFrame(data)     # Convert the queryset to a DataFrame
        df['question__slug'] = df['question__slug'].map(labelMap)

    df['simpleCC'] = df['simpleCC'].map(cc_mapping)
    missing_cats = True if df['simpleCC'].nunique() < 3 else False

    # clip values to [0,1] since the collaboration boost/discount can push coverage over 1.0 and under 0
    df['average'] =  df['average'].clip(lower=0.0, upper=1.0)
    # Multiply by 100 to display percentages
    df['average'] *= 100
    df['stddev'] *= 100

    # Rename the columns for clarity
    if topic == 'all':
        df= df.rename(columns={'question__topic__slug' : 'Topics','average':'Average Value',})
        yName = 'Topics'
    else:
        df= df.rename(columns={'question__slug' : 'Questions','average':'Average Value',})
        yName = 'Questions'

    #markerscale = (abs(height)/DEFAULT_HEIGHT)
    markerscale = 1-((1-(abs(height)/DEFAULT_HEIGHT))*1.3)
    # textscale = 1-((1-markerscale)*.6)
    textscale = 0.9-((1-markerscale)*.3)


    if height <= CALCULATE_SCALED_HEIGHT:
        legendCount = 3
        if(benchmarks!=None):
            legendCount = legendCount+len(benchmarks)
        height = calculateScaledHeight(len(yvalues), legendCount, abs(height))

    #print(f'topicCapsDataGraphByCC WxH:{width}x{height} markerscale: {markerscale} textscale: {textscale}')

    # Create a grouped bar chart
    fig = px.bar(df, y=yName, x='Average Value',error_x='stddev' if showErrBars else None,
                color='simpleCC', 
                color_discrete_map={'R1':colorPalette['R1'], 'R2':colorPalette['R2'],'Other Acad.':colorPalette['OtherAcad']},
                barmode='group', # Use 'group' for grouped bars
                labels={'question__topic__slug': '', 'average': '', 'simpleCC':dataviz.DataFilterForm.CARN_CLASS},
                width=width, height=height )
    applyStandardHBarFormatting(fig, textscale=textscale)

    # If benchmark data passed in, layer that over
    if(benchmarks!=None) :
        # We add them in reverse order so the most recent is on top
        imarker = min(len(benchmarks), NMARKERSMAX)-1
        while imarker >= 0:
            bm = benchmarks[imarker]
            if bm['hasData']:
                bmName = bm['name']
            else:
                bmName = '<span style="font-style:italic;fill:'+colorPalette['noDataLegendFontColor']+';">'+bm['name']+'</em>'
            fig.add_trace(go.Scatter(y=yvalues, x=bm['data'], mode='markers', 
                                        marker_color=barmarkercolors[imarker], marker_line_width=2, marker_line_color='white',
                                        marker_size=MARKER_SZ*markerscale*barmarkerscales[imarker], marker_symbol=hbarmarkertypes[imarker], 
                                        name=bmName))
            imarker-=1
        fig.update_traces(hovertemplate = 'Coverage: %{x:.1f}%<extra></extra>')

    return po.to_html(fig, include_plotlyjs=INCLUDE_PLOTLYJS, full_html=True), missing_cats

def capsDataGraphByMission(answers, benchmarks=None, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT, showErrBars=True):
    #print("capsDataGraphByMission with: ", answers.count()," answers")
    if (answers.count() == 0): 
        return None
    answers = answers.annotate(mission2=Case(
        # Since most old profiles have Null for Mission, let's map it
        When(assessment__profile__mission__isnull=True, then=Value(VALUE_UNKNOWN)),  
        default=F('assessment__profile__mission') ))
    data = answers.aggregate_score('question__topic__facing','mission2').values('question__topic__facing','mission2','average','stddev')
    df = pd.DataFrame(data)     # Convert the queryset to a DataFrame
    # Map the facings values to names
    df['question__topic__facing'] = df['question__topic__facing'].map(Facing_mapping)
    df['mission2'] = df['mission2'].map(mission_mapping)
    missing_cats = True if df['mission2'].nunique() < len(mission_mapping) else False

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
    # Enforce the original sorting that we define in the enumeration for Mission
    df['mission2'] = pd.Categorical(df['mission2'], categories=mission_mapping.values(), ordered=True)
    df = df.sort_values(['Facings', 'mission2'])
    #print(df)

    markerscale = 1.3-((1-(abs(height)/DEFAULT_HEIGHT))*1.4)
    textscale = 1-((1.3-markerscale)*.4)
    # Create a grouped bar chart
    fig = px.bar(df, x='Facings', y='Average Value',error_y='stddev' if showErrBars else None,
                color='mission2', 
                color_discrete_map=mission_palette,
                barmode='group', # Use 'group' for grouped bars
                width=width, height=height )
    applyStandardVBarFormatting(fig, textscale=textscale, nCats=4)

    # If benchmark data passed in, layer that over
    # At the top level, no benchmark will be empty, even if it has no data for some facing
    if(benchmarks!=None) :
        # We add them in reverse order so the most recent is on top
        imarker = min(len(benchmarks), NMARKERSMAX)-1
        while imarker >= 0:
            bm = benchmarks[imarker]
            fig.add_trace(go.Scatter(x=Facing_xvals, y=bm['data'], mode='markers', 
                                        marker_color=barmarkercolors[imarker], marker_line_width=2, marker_line_color='white',
                                        marker_size=MARKER_SZ*markerscale*barmarkerscales[imarker], marker_symbol=vbarmarkertypes[imarker], name=bm['name']))
            imarker-=1
        fig.update_traces(hovertemplate = 'Coverage: %{y:.1f}%<extra></extra>')

    return po.to_html(fig, include_plotlyjs=INCLUDE_PLOTLYJS, full_html=True), missing_cats

def facingCapsDataGraphByMission(answers, facing, topic, benchmarks=None, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT, showErrBars=True):
    #print(f'facingCapsDataGraphByMission({facing},{topic}) with: {answers.count()} answers')
    if (answers.count() == 0): 
        return None
    answers = answers.filter(question__topic__facing__slug=facing)
    if topic != 'all':
        answers = answers.filter(question__topic__slug=topic)
    
    annotatedAnswers = answers.annotate(mission2=Case(
        # Since most old profiles have Null for Mission, let's map it
        When(assessment__profile__mission__isnull=True, then=Value(VALUE_UNKNOWN)),  
        default=F('assessment__profile__mission') ))
    
    # Note that answers has been pre-filtered of domain topic and not_applicable answers
    if topic == 'all':
        annotatedAnswers = annotatedAnswers.order_by('question__topic__index', 'mission2')
        data = annotatedAnswers.aggregate_score('question__topic__slug','mission2')\
                    .values('question__topic__slug','mission2','average','stddev')
        # Map the topic slugs to names
        labelMap, yvalues = labelMapForFacing(facing)
        df = pd.DataFrame(data)     # Convert the queryset to a DataFrame
        df['question__topic__slug'] = df['question__topic__slug'].map(labelMap)
    else:
        annotatedAnswers = annotatedAnswers.order_by('question__index', 'mission2')
        data = annotatedAnswers.aggregate_score('question__slug','mission2')\
                    .values('question__slug','mission2','average','stddev')
        # Map the topic slugs to names
        labelMap, yvalues = labelMapForTopic(facing, topic)
        df = pd.DataFrame(data)     # Convert the queryset to a DataFrame
        df['question__slug'] = df['question__slug'].map(labelMap)

    df['mission2'] = df['mission2'].map(mission_mapping)
    missing_cats = True if df['mission2'].nunique() < len(mission_mapping) else False

    # clip values to [0,1] since the collaboration boost/discount can push coverage over 1.0 and under 0
    df['average'] =  df['average'].clip(lower=0.0, upper=1.0)
    # Multiply by 100 to display percentages
    df['average'] *= 100
    df['stddev'] *= 100

    # Rename the columns for clarity
    if topic == 'all':
        df= df.rename(columns={'question__topic__slug' : 'Topics','average':'Average Value',})
        yName = 'Topics'
    else:
        df= df.rename(columns={'question__slug' : 'Questions','average':'Average Value',})
        yName = 'Questions'
    # Enforce the original sorting that we define in the enumeration for Mission
    df['mission2'] = pd.Categorical(df['mission2'], categories=mission_mapping.values(), ordered=True)
    df = df.sort_values([yName, 'mission2'])
    
    #markerscale = (abs(height)/DEFAULT_HEIGHT)
    markerscale = 1-((1-(abs(height)/DEFAULT_HEIGHT))*1.3)
    textscale = 0.9-((1-markerscale)*.3)

    # We have 4 sub-cats, so scale the height very slightly for topics with few questions
    if height <= CALCULATE_SCALED_HEIGHT:
        legendCount = len(mission_mapping)
        if(benchmarks!=None):
            legendCount = legendCount+len(benchmarks)
        height = calculateScaledHeight(len(yvalues), legendCount, abs(height), lowCountAdj=.7)

    # Create a grouped bar chart
    fig = px.bar(df, y=yName, x='Average Value',error_x='stddev' if showErrBars else None,
                color='mission2',
                color_discrete_map=mission_palette,
                barmode='group', # Use 'group' for grouped bars
                width=width, height=height )
    applyStandardHBarFormatting(fig, textscale=textscale, nCats=4)

    # If benchmark data passed in, layer that over
    if(benchmarks!=None) :
        # We add them in reverse order so the most recent is on top
        imarker = min(len(benchmarks), NMARKERSMAX)-1
        while imarker >= 0:
            bm = benchmarks[imarker]
            if bm['hasData']:
                bmName = bm['name']
            else:
                bmName = '<span style="font-style:italic;fill:'+colorPalette['noDataLegendFontColor']+';">'+bm['name']+'</em>'
            fig.add_trace(go.Scatter(y=yvalues, x=bm['data'], mode='markers', 
                                        marker_color=barmarkercolors[imarker], marker_line_width=2, marker_line_color='white',
                                        marker_size=MARKER_SZ*markerscale*barmarkerscales[imarker], marker_symbol=hbarmarkertypes[imarker], 
                                        name=bmName))
            imarker-=1
        fig.update_traces(hovertemplate = 'Coverage: %{x:.1f}%<extra></extra>')

    return po.to_html(fig, include_plotlyjs=INCLUDE_PLOTLYJS, full_html=True), missing_cats

def capsDataGraphByPubPriv(answers, benchmarks=None, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT, showErrBars=True):
    #print("capsDataGraphByCC with: ", answers.count()," answers")
    if (answers.count() == 0): 
        return None
    answers = answers.filter(assessment__profile__institution__ipeds_control__isnull=False)
    # Note that answers has been pre-filtered of domain topic and not_applicable answers
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
    missing_cats = True if df['assessment__profile__institution__ipeds_control'].nunique() < 2 else False

    # Rename the columns for clarity
    df =  df.rename(columns={
            'question__topic__facing' : 'Facings',
            'assessment__profile__institution__ipeds_control' :'Public/Private',
            'average':'Average Values',
        })

    markerscale = 1.3-((1-(abs(height)/DEFAULT_HEIGHT))*1.4)
    textscale = 1-((1.3-markerscale)*.4)
    # Create a grouped bar chart
    fig = px.bar( df, x='Facings', y='Average Values',error_y='stddev' if showErrBars else None,
                    barmode='group',  # Use 'group' for grouped bars
                    color='Public/Private',
                    color_discrete_map={'Public': colorPalette['Public'], 'Private': colorPalette['Private']},  # Set custom color
                    labels={'Facings': 'Facings', 'value': 'Average Values'},
                    width=width, height=height)
    applyStandardVBarFormatting(fig, textscale=textscale)

    # If benchmark data passed in, layer that over
    # At the top level, no benchmark will be empty, even if it has no data for some facing
    if(benchmarks!=None) :
        # We add them in reverse order so the most recent is on top
        imarker = min(len(benchmarks), NMARKERSMAX)-1
        while imarker >= 0:
            bm = benchmarks[imarker]
            fig.add_trace(go.Scatter(x=Facing_xvals, y=bm['data'], mode='markers', 
                                        marker_color=barmarkercolors[imarker], marker_line_width=2, marker_line_color='white',
                                        marker_size=MARKER_SZ*markerscale*barmarkerscales[imarker], marker_symbol=vbarmarkertypes[imarker], name=bm['name']))
            imarker-=1
        fig.update_traces(hovertemplate = 'Coverage: %{y:.1f}%<extra></extra>')

    # Convert the figure to HTML including Plotly.js
    return po.to_html(fig, include_plotlyjs=INCLUDE_PLOTLYJS, full_html=True), missing_cats

def facingCapsDataGraphByPubPriv(answers, facing, topic, benchmarks=None, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT, showErrBars=True):
    #print("facingCapsDataGraphByPubPriv with: ", answers.count()," answers")
    if (answers.count() == 0): 
        return None
    answers = answers.filter(assessment__profile__institution__ipeds_control__isnull=False)\
                            .filter(question__topic__facing__slug=facing)
    # Note that answers has been pre-filtered of domain topic and not_applicable answers
    if topic == 'all':
        answers = answers.order_by('question__topic__index', 
                                      'assessment__profile__institution__ipeds_control')
        data = answers.aggregate_score('question__topic__slug','assessment__profile__institution__ipeds_control')\
                    .values('question__topic__slug',
                            'assessment__profile__institution__ipeds_control','average','stddev')
        # Map the topic slugs to names
        labelMap, yvalues = labelMapForFacing(facing)
        df = pd.DataFrame(data)     # Convert the queryset to a DataFrame
        df['question__topic__slug'] = df['question__topic__slug'].map(labelMap)
    else:
        answers = answers.filter(question__topic__slug=topic).order_by('question__index', 
                                      'assessment__profile__institution__ipeds_control')
        data = answers.aggregate_score('question__slug','assessment__profile__institution__ipeds_control')\
                    .values('question__slug',
                            'assessment__profile__institution__ipeds_control','average','stddev')
        # Map the question slugs to names
        labelMap, yvalues = labelMapForTopic(facing, topic)
        df = pd.DataFrame(data)     # Convert the queryset to a DataFrame
        df['question__slug'] = df['question__slug'].map(labelMap)

    # print(f'Unique yValues:{len(yvalues)}')
    df['assessment__profile__institution__ipeds_control'] = \
        df['assessment__profile__institution__ipeds_control'].map(pubpriv_mapping)

    # clip values to [0,1] since the collaboration boost/discount can push coverage over 1.0 and under 0
    df['average'] =  df['average'].clip(lower=0.0, upper=1.0)
    # Multiply by 100 to display percentages
    df['average'] *= 100
    df['stddev'] *= 100
    missing_cats = True if df['assessment__profile__institution__ipeds_control'].nunique() < 2 else False

    # Rename the columns for clarity
    if topic == 'all':
        df= df.rename(columns={'question__topic__slug' : 'Topics',
                               'assessment__profile__institution__ipeds_control' :'Public/Private','average':'Average Value',})
        yName = 'Topics'
    else:
        df= df.rename(columns={'question__slug' : 'Questions',
                               'assessment__profile__institution__ipeds_control' :'Public/Private','average':'Average Value',})
        yName = 'Questions'
    
    #markerscale = (abs(height)/DEFAULT_HEIGHT)
    markerscale = 1-((1-(abs(height)/DEFAULT_HEIGHT))*1.3)
    textscale = 0.9-((1-markerscale)*.3)

    if height <= CALCULATE_SCALED_HEIGHT:
        legendCount = 2
        if(benchmarks!=None):
            legendCount = legendCount+len(benchmarks)
        height = calculateScaledHeight(len(yvalues), legendCount, abs(height))
    
    # Create a grouped bar chart
    fig = px.bar(df, y=yName, x='Average Value',error_x='stddev' if showErrBars else None,
                color='Public/Private',
                color_discrete_map={'Public': colorPalette['Public'], 'Private': colorPalette['Private']},  # Set custom color
                barmode='group', # Use 'group' for grouped bars
                width=width, height=height )
    applyStandardHBarFormatting(fig, textscale=textscale)

    # If benchmark data passed in, layer that over
    if(benchmarks!=None) :
        # We add them in reverse order so the most recent is on top
        imarker = min(len(benchmarks), NMARKERSMAX)-1
        while imarker >= 0:
            bm = benchmarks[imarker]
            if bm['hasData']:
                bmName = bm['name']
            else:
                bmName = '<span style="font-style:italic;fill:'+colorPalette['noDataLegendFontColor']+';">'+bm['name']+'</em>'
            fig.add_trace(go.Scatter(y=yvalues, x=bm['data'], mode='markers', 
                                        marker_color=barmarkercolors[imarker], marker_line_width=2, marker_line_color='white',
                                        marker_size=MARKER_SZ*markerscale*barmarkerscales[imarker], marker_symbol=hbarmarkertypes[imarker], 
                                        name=bmName))
            imarker-=1
        fig.update_traces(hovertemplate = 'Coverage: %{x:.1f}%<extra></extra>')

    return po.to_html(fig, include_plotlyjs=INCLUDE_PLOTLYJS, full_html=True), missing_cats

def capsDataGraphByEPSCoR(answers, benchmarks=None, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT, showErrBars=True):
    #print("capsDataGraphByEPSCoR with: ", answers.count()," answers")
    if (answers.count() == 0): 
        return None
    # Note that answers has been pre-filtered of domain topic and not_applicable answers
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
    missing_cats = True if df['assessment__profile__institution__ipeds_epscor'].nunique() < 2 else False

    # Rename the columns for clarity
    df =  df.rename(columns={
            'question__topic__facing' : 'Facings',
            'assessment__profile__institution__ipeds_epscor' :'EPSCoR',
            'average':'Average Values',
        })

    markerscale = 1.3-((1-(abs(height)/DEFAULT_HEIGHT))*1.4)
    textscale = 1-((1.3-markerscale)*.4)
    # Create a grouped bar chart
    fig = px.bar( df, x='Facings', y='Average Values',error_y='stddev' if showErrBars else None,
                    barmode='group',  # Use 'group' for grouped bars
                    color='EPSCoR',
                    color_discrete_map={Institution.EPSCORChoices.EPSCOR.label: colorPalette['EPSCoR'], 
                                        Institution.EPSCORChoices.NOT_EPSCOR.label: colorPalette['nonEPSCoR']},  # Set custom color
                    width=width, height=height)
    applyStandardVBarFormatting(fig, textscale=textscale)

    # If benchmark data passed in, layer that over
    # At the top level, no benchmark will be empty, even if it has no data for some facing
    if(benchmarks!=None) :
        # We add them in reverse order so the most recent is on top
        imarker = min(len(benchmarks), NMARKERSMAX)-1
        while imarker >= 0:
            bm = benchmarks[imarker]
            fig.add_trace(go.Scatter(x=Facing_xvals, y=bm['data'], mode='markers', 
                                        marker_color=barmarkercolors[imarker], marker_line_width=2, marker_line_color='white',
                                        marker_size=MARKER_SZ*markerscale*barmarkerscales[imarker], marker_symbol=vbarmarkertypes[imarker], name=bm['name']))
            imarker-=1
        fig.update_traces(hovertemplate = 'Coverage: %{y:.1f}%<extra></extra>')

    # Convert the figure to HTML including Plotly.js
    return po.to_html(fig, include_plotlyjs=INCLUDE_PLOTLYJS, full_html=True), missing_cats

def facingCapsDataGraphByEPSCoR(answers, facing, topic, benchmarks=None, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT, showErrBars=True):
    #print("facingCapsDataGraphByEPSCoR with: ", answers.count()," answers")
    if (answers.count() == 0): 
        return None
    answers = answers.filter(assessment__profile__institution__ipeds_epscor__isnull=False)\
                            .filter(question__topic__facing__slug=facing)

    # Note that answers has been pre-filtered of domain topic and not_applicable answers
    if topic == 'all':
        answers = answers.order_by('question__topic__index', 
                                      'assessment__profile__institution__ipeds_epscor')
        data = answers.aggregate_score('question__topic__slug','assessment__profile__institution__ipeds_epscor')\
                        .values('question__topic__slug',
                                'assessment__profile__institution__ipeds_epscor','average','stddev')
        df = pd.DataFrame(data)     # Convert the queryset to a DataFrame
        # Map the topic slugs to names
        labelMap, yvalues = labelMapForFacing(facing)
        df['question__topic__slug'] = df['question__topic__slug'].map(labelMap)
    else: 
        answers = answers.filter(question__topic__slug=topic).order_by('question__index', 
                                      'assessment__profile__institution__ipeds_epscor')
        data = answers.aggregate_score('question__slug','assessment__profile__institution__ipeds_epscor')\
                        .values('question__slug',
                                'assessment__profile__institution__ipeds_epscor','average','stddev')
        df = pd.DataFrame(data)     # Convert the queryset to a DataFrame
        # Map the topic slugs to names
        labelMap, yvalues = labelMapForTopic(facing, topic)
        df['question__slug'] = df['question__slug'].map(labelMap)

    df['assessment__profile__institution__ipeds_epscor'] = \
        df['assessment__profile__institution__ipeds_epscor'].map(epscor_mapping)

    # clip values to [0,1] since the collaboration boost/discount can push coverage over 1.0 and under 0
    df['average'] =  df['average'].clip(lower=0.0, upper=1.0)
    # Multiply by 100 to display percentages
    df['average'] *= 100
    df['stddev'] *= 100
    missing_cats = True if df['assessment__profile__institution__ipeds_epscor'].nunique() < 2 else False

    # Rename the columns for clarity
    if topic == 'all':
        df= df.rename(columns={'question__topic__slug' : 'Topics',
                'assessment__profile__institution__ipeds_epscor' :'EPSCoR','average':'Average Value',})
        yName = 'Topics'
    else:
        df= df.rename(columns={'question__slug' : 'Questions',
                'assessment__profile__institution__ipeds_epscor' :'EPSCoR','average':'Average Value',})
        yName = 'Questions'
    
    #markerscale = (abs(height)/DEFAULT_HEIGHT)
    markerscale = 1-((1-(abs(height)/DEFAULT_HEIGHT))*1.3)
    textscale = 0.9-((1-markerscale)*.3)

    if height <= CALCULATE_SCALED_HEIGHT:
        legendCount = 2
        if(benchmarks!=None):
            legendCount = legendCount+len(benchmarks)
        height = calculateScaledHeight(len(yvalues), legendCount, abs(height))
    
    # Create a grouped bar chart
    fig = px.bar(df, y=yName, x='Average Value',error_x='stddev' if showErrBars else None,
                color='EPSCoR',
                color_discrete_map={Institution.EPSCORChoices.EPSCOR.label: colorPalette['EPSCoR'], 
                                    Institution.EPSCORChoices.NOT_EPSCOR.label: colorPalette['nonEPSCoR']},  # Set custom color
                barmode='group', # Use 'group' for grouped bars
                width=width, height=height )
    applyStandardHBarFormatting(fig, textscale=textscale)

    # If benchmark data passed in, layer that over
    if benchmarks!=None:
        # We add them in reverse order so the most recent is on top
        imarker = min(len(benchmarks), NMARKERSMAX)-1
        while imarker >= 0:
            bm = benchmarks[imarker]
            if bm['hasData']:
                bmName = bm['name']
            else:
                bmName = '<span style="font-style:italic;fill:'+colorPalette['noDataLegendFontColor']+';">'+bm['name']+'</em>'
            fig.add_trace(go.Scatter(y=yvalues, x=bm['data'], mode='markers', 
                                        marker_color=barmarkercolors[imarker], marker_line_width=2, marker_line_color='white',
                                        marker_size=MARKER_SZ*markerscale*barmarkerscales[imarker], marker_symbol=hbarmarkertypes[imarker], 
                                        name=bmName))
            imarker-=1
        fig.update_traces(hovertemplate = 'Coverage: %{x:.1f}%<extra></extra>')

    return po.to_html(fig, include_plotlyjs=INCLUDE_PLOTLYJS, full_html=True), missing_cats

def capsDataGraphByMSI(answers, benchmarks=None, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT, showErrBars=True):
    #print("capsDataGraphByMSI with: ", answers.count()," answers")
    if (answers.count() == 0): 
        return None
    
    # Note that answers has been pre-filtered of domain topic and not_applicable answers
    answers = answers.filter(Q(assessment__profile__institution__ipeds_msi__isnull=False))
    data = answers.aggregate_score('question__topic__facing','assessment__profile__institution__ipeds_msi'). \
        values('question__topic__facing','assessment__profile__institution__ipeds_msi','average','stddev')

    df= pd.DataFrame(data)
    df['question__topic__facing'] = df['question__topic__facing'].map(Facing_mapping) # Map the classification values to names

    # Map the values to names
    df['assessment__profile__institution__ipeds_msi'] =  df['assessment__profile__institution__ipeds_msi'].map(msi_mapping)
    # clip values to [0,1] since the collaboration boost/discount can push coverage over 1.0 and under 0
    df['average'] =  df['average'].clip(lower=0.0, upper=1.0)
    # Multiply by 100 to display percentages
    df['average'] *= 100
    df['stddev'] *= 100
    missing_cats = True if df['assessment__profile__institution__ipeds_msi'].nunique() < 2 else False

    # Rename the columns for clarity
    df =  df.rename(columns={
            'question__topic__facing' : 'Facings',
            'assessment__profile__institution__ipeds_msi' :'MSI',
            'average':'Average Values',
        })

    markerscale = 1.3-((1-(abs(height)/DEFAULT_HEIGHT))*1.4)
    textscale = 1-((1.3-markerscale)*.4)
    # Create a grouped bar chart
    fig = px.bar( df, x='Facings', y='Average Values',error_y='stddev' if showErrBars else None,
                    barmode='group',  # Use 'group' for grouped bars
                    color='MSI',
                    color_discrete_map={Institution.MSIChoices.MSI.label: colorPalette['otherMSI'], 
                                        Institution.MSIChoices.NOT_AN_MSI.label: colorPalette['NotMSI']},  # Set custom color
                    width=width, height=height)
    applyStandardVBarFormatting(fig, textscale=textscale)

    # If benchmark data passed in, layer that over
    # At the top level, no benchmark will be empty, even if it has no data for some facing
    if(benchmarks!=None) :
        # We add them in reverse order so the most recent is on top
        imarker = min(len(benchmarks), NMARKERSMAX)-1
        while imarker >= 0:
            bm = benchmarks[imarker]
            fig.add_trace(go.Scatter(x=Facing_xvals, y=bm['data'], mode='markers', 
                                        marker_color=barmarkercolors[imarker], marker_line_width=2, marker_line_color='white',
                                        marker_size=MARKER_SZ*markerscale*barmarkerscales[imarker], marker_symbol=vbarmarkertypes[imarker], name=bm['name']))
            imarker-=1
        fig.update_traces(hovertemplate = 'Coverage: %{y:.1f}%<extra></extra>')

    # Convert the figure to HTML including Plotly.js
    return po.to_html(fig, include_plotlyjs=INCLUDE_PLOTLYJS, full_html=True), missing_cats

def facingCapsDataGraphByMSI(answers, facing, topic, benchmarks=None, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT, showErrBars=True):
    #print("facingCapsDataGraphByMSI with: ", answers.count()," answers")
    if (answers.count() == 0): 
        return None
    answers = answers.filter(assessment__profile__institution__ipeds_msi__isnull=False)\
                            .filter(question__topic__facing__slug=facing)
    
    # Note that answers has been pre-filtered of domain topic and not_applicable answers
    if topic == 'all':
        answers = answers.order_by('question__topic__index', 
                                      'assessment__profile__institution__ipeds_msi')
        data = answers.aggregate_score('question__topic__slug','assessment__profile__institution__ipeds_msi')\
                        .values('question__topic__slug',
                                'assessment__profile__institution__ipeds_msi','average','stddev')
        df = pd.DataFrame(data)     # Convert the queryset to a DataFrame
        # Map the topic slugs to names
        labelMap, yvalues = labelMapForFacing(facing)
        df['question__topic__slug'] = df['question__topic__slug'].map(labelMap)
    else:
        answers = answers.filter(question__topic__slug=topic).order_by('question__index', 
                                      'assessment__profile__institution__ipeds_msi')
        data = answers.aggregate_score('question__slug','assessment__profile__institution__ipeds_msi')\
                        .values('question__slug',
                                'assessment__profile__institution__ipeds_msi','average','stddev')
        df = pd.DataFrame(data)     # Convert the queryset to a DataFrame
        # Map the topic slugs to names
        labelMap, yvalues = labelMapForTopic(facing, topic)
        df['question__slug'] = df['question__slug'].map(labelMap)


    df['assessment__profile__institution__ipeds_msi'] = \
        df['assessment__profile__institution__ipeds_msi'].map(msi_mapping)

    # clip values to [0,1] since the collaboration boost/discount can push coverage over 1.0 and under 0
    df['average'] =  df['average'].clip(lower=0.0, upper=1.0)
    # Multiply by 100 to display percentages
    df['average'] *= 100
    df['stddev'] *= 100
    missing_cats = True if df['assessment__profile__institution__ipeds_msi'].nunique() < 2 else False

    # Rename the columns for clarity
    if topic == 'all':
        df= df.rename(columns={'question__topic__slug' : 'Topics',
                'assessment__profile__institution__ipeds_msi' :'MSI','average':'Average Value',})
        yName = 'Topics'
    else:
        df= df.rename(columns={'question__slug' : 'Questions',
                'assessment__profile__institution__ipeds_msi' :'MSI','average':'Average Value',})
        yName = 'Questions'
    
    #markerscale = (abs(height)/DEFAULT_HEIGHT)
    markerscale = 1-((1-(abs(height)/DEFAULT_HEIGHT))*1.3)
    textscale = 0.9-((1-markerscale)*.3)

    if height <= CALCULATE_SCALED_HEIGHT:
        legendCount = 2
        if(benchmarks!=None):
            legendCount = legendCount+len(benchmarks)
        height = calculateScaledHeight(len(yvalues), legendCount, abs(height))

    # Create a grouped bar chart
    fig = px.bar(df, y=yName, x='Average Value',error_x='stddev' if showErrBars else None,
                color='MSI',
                color_discrete_map={Institution.MSIChoices.MSI.label: colorPalette['otherMSI'], 
                                    Institution.MSIChoices.NOT_AN_MSI.label: colorPalette['NotMSI']},  # Set custom color
                barmode='group', # Use 'group' for grouped bars
                width=width, height=height )
    applyStandardHBarFormatting(fig, textscale=textscale)

    # If benchmark data passed in, layer that over
    if(benchmarks!=None) :
        # We add them in reverse order so the most recent is on top
        imarker = min(len(benchmarks), NMARKERSMAX)-1
        while imarker >= 0:
            bm = benchmarks[imarker]
            if bm['hasData']:
                bmName = bm['name']
            else:
                bmName = '<span style="font-style:italic;fill:'+colorPalette['noDataLegendFontColor']+';">'+bm['name']+'</em>'
            fig.add_trace(go.Scatter(y=yvalues, x=bm['data'], mode='markers', 
                                        marker_color=barmarkercolors[imarker], marker_line_width=2, marker_line_color='white',
                                        marker_size=MARKER_SZ*markerscale*barmarkerscales[imarker], marker_symbol=hbarmarkertypes[imarker], 
                                        name=bmName))
            imarker-=1
        fig.update_traces(hovertemplate = 'Coverage: %{x:.1f}%<extra></extra>')

    return po.to_html(fig, include_plotlyjs=INCLUDE_PLOTLYJS, full_html=True), missing_cats

def capsDataGraphByOrgModel(answers, benchmarks=None, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT, showErrBars=True):
    # Org Model is call "structure" in the model - not very useful until we have more metadata. Sigh. 
    # print("capsDataGraphByOrgModel with: ", answers.count()," answers")
    if (answers.count() == 0): 
        return None
    answers = answers.annotate(structure2=Case(
        # Since most old profiles have Null for Mission, let's map it
        When(assessment__profile__structure__isnull=True, then=Value(VALUE_UNKNOWN)),  
        default=F('assessment__profile__structure') ))
    data = answers.aggregate_score('question__topic__facing','structure2'). \
        values('question__topic__facing','structure2','average','stddev')

    df= pd.DataFrame(data)
    df['question__topic__facing'] = df['question__topic__facing'].map(Facing_mapping) # Map the classification values to names
    df['structure2'] =  df['structure2'].map(structure_mapping)
    missing_cats = True if df['structure2'].nunique() < len(structure_mapping) else False

    # clip values to [0,1] since the collaboration boost/discount can push coverage over 1.0 and under 0
    df['average'] =  df['average'].clip(lower=0.0, upper=1.0)
    # Multiply by 100 to display percentages
    df['average'] *= 100
    df['stddev'] *= 100

    # Rename the columns for clarity
    df =  df.rename(columns={
            'question__topic__facing' : 'Facings',
            'structure2' :'OrgModel',
            'average':'Average Values',
        })

    markerscale = 1.3-((1-(abs(height)/DEFAULT_HEIGHT))*1.4)
    textscale = 1-((1.3-markerscale)*.4)
    # Create a grouped bar chart
    fig = px.bar( df, x='Facings', y='Average Values',error_y='stddev' if showErrBars else None,
                    barmode='group',  # Use 'group' for grouped bars
                    color='OrgModel',
                    color_discrete_map=structure_palette,
                    labels={'Facings': 'Facings', 'value': 'Average Values'},
                    width=width, height=height)
    applyStandardVBarFormatting(fig, textscale=textscale, nCats=4)

    # If benchmark data passed in, layer that over
    # At the top level, no benchmark will be empty, even if it has no data for some facing
    if(benchmarks!=None) :
        # We add them in reverse order so the most recent is on top
        imarker = min(len(benchmarks), NMARKERSMAX)-1
        while imarker >= 0:
            bm = benchmarks[imarker]
            fig.add_trace(go.Scatter(x=Facing_xvals, y=bm['data'], mode='markers', 
                                        marker_color=barmarkercolors[imarker], marker_line_width=2, marker_line_color='white',
                                        marker_size=MARKER_SZ*markerscale*barmarkerscales[imarker], marker_symbol=vbarmarkertypes[imarker], name=bm['name']))
            imarker-=1
        fig.update_traces(hovertemplate = 'Coverage: %{y:.1f}%<extra></extra>')

    # Convert the figure to HTML including Plotly.js
    return po.to_html(fig, include_plotlyjs=INCLUDE_PLOTLYJS, full_html=True), missing_cats

def facingCapsDataGraphByOrgModel(answers, facing, topic, benchmarks=None, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT, showErrBars=True):
    #print("facingCapsDataGraphByOrgModel with: ", answers.count()," answers")
    if (answers.count() == 0): 
        return None
    answers = answers.filter(question__topic__facing__slug=facing)
    answers = answers.annotate(structure2=Case(
        # Since most old profiles have Null for Mission, let's map it
        When(assessment__profile__structure__isnull=True, then=Value(VALUE_UNKNOWN)),  
        default=F('assessment__profile__structure') ))

    # Note that answers has been pre-filtered of domain topic and not_applicable answers
    if topic == 'all':
        answers = answers.order_by('question__topic__index', 'structure2')
        data = answers.aggregate_score('question__topic__slug','structure2')\
                    .values('question__topic__slug','structure2','average','stddev')
        df = pd.DataFrame(data)     # Convert the queryset to a DataFrame
        # Map the topic slugs to names
        labelMap, yvalues = labelMapForFacing(facing)
        df['question__topic__slug'] = df['question__topic__slug'].map(labelMap)
    else:
        answers = answers.filter(question__topic__slug=topic).order_by('question__index', 'structure2')
        data = answers.aggregate_score('question__slug','structure2')\
                    .values('question__slug','structure2','average','stddev')
        df = pd.DataFrame(data)     # Convert the queryset to a DataFrame
        # Map the topic slugs to names
        labelMap, yvalues = labelMapForTopic(facing, topic)
        df['question__slug'] = df['question__slug'].map(labelMap)

    df['structure2'] = df['structure2'].map(structure_mapping)
    missing_cats = True if df['structure2'].nunique() < len(structure_mapping) else False

    # clip values to [0,1] since the collaboration boost/discount can push coverage over 1.0 and under 0
    df['average'] =  df['average'].clip(lower=0.0, upper=1.0)
    # Multiply by 100 to display percentages
    df['average'] *= 100
    df['stddev'] *= 100

    # Rename the columns for clarity
    if topic == 'all':
        df= df.rename(columns={'question__topic__slug' : 'Topics','average':'Average Value',})
        yName = 'Topics'
    else:
        df= df.rename(columns={'question__slug' : 'Questions','average':'Average Value',})
        yName = 'Questions'
    
    #markerscale = (abs(height)/DEFAULT_HEIGHT)
    markerscale = 1-((1-(abs(height)/DEFAULT_HEIGHT))*1.3)
    textscale = 0.9-((1-markerscale)*.3)

    if height <= CALCULATE_SCALED_HEIGHT:
        legendCount = len(structure_mapping)
        if(benchmarks!=None):
            legendCount = legendCount+len(benchmarks)
        height = calculateScaledHeight(len(yvalues), legendCount, abs(height))
        print(f'facingCapsDataGraphByOrgModel scaling height to: {height}')
    
    # Create a grouped bar chart
    fig = px.bar(df, y=yName, x='Average Value',error_x='stddev' if showErrBars else None,
                color='structure2',
                color_discrete_map=structure_palette,
                barmode='group', # Use 'group' for grouped bars
                width=width, height=height )
    applyStandardHBarFormatting(fig, textscale=textscale, nCats=4)

    # If benchmark data passed in, layer that over
    if(benchmarks!=None) :
        # We add them in reverse order so the most recent is on top
        imarker = min(len(benchmarks), NMARKERSMAX)-1
        while imarker >= 0:
            bm = benchmarks[imarker]
            if bm['hasData']:
                bmName = bm['name']
            else:
                bmName = '<span style="font-style:italic;fill:'+colorPalette['noDataLegendFontColor']+';">'+bm['name']+'</em>'
            fig.add_trace(go.Scatter(y=yvalues, x=bm['data'], mode='markers', 
                                        marker_color=barmarkercolors[imarker], marker_line_width=2, marker_line_color='white',
                                        marker_size=MARKER_SZ*markerscale*barmarkerscales[imarker], marker_symbol=hbarmarkertypes[imarker], 
                                        name=bmName))
            imarker-=1
        fig.update_traces(hovertemplate = 'Coverage: %{x:.1f}%<extra></extra>')

    return po.to_html(fig, include_plotlyjs=INCLUDE_PLOTLYJS, full_html=True), missing_cats

def capsDataGraphByReporting(answers, benchmarks=None,
                           width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT, showErrBars=True):
    # Org Model is call "orgchart" in the model - not very useful until we have more metadata. Sigh. 
    # print("capsDataGraphByReporting with: ", answers.count()," answers")
    if (answers.count() == 0): 
        return None
    answers = answers.annotate(reporting2=Case(
        # Since most old profiles have Null for Mission, let's map it
        When(assessment__profile__org_chart__isnull=True, then=Value(VALUE_UNKNOWN)),  
        default=F('assessment__profile__org_chart') ))
    data = answers.aggregate_score('question__topic__facing','reporting2'). \
        values('question__topic__facing','reporting2','average','stddev')

    df= pd.DataFrame(data)
    df['question__topic__facing'] = df['question__topic__facing'].map(Facing_mapping) # Map the classification values to names
    df['reporting2'] =  df['reporting2'].map(reporting_mapping)
    missing_cats = True if df['reporting2'].nunique() < len(reporting_mapping) else False

    # clip values to [0,1] since the collaboration boost/discount can push coverage over 1.0 and under 0
    df['average'] =  df['average'].clip(lower=0.0, upper=1.0)
    # Multiply by 100 to display percentages
    df['average'] *= 100
    df['stddev'] *= 100

    # Rename the columns for clarity
    df =  df.rename(columns={
            'question__topic__facing' : 'Facings',
            'average':'Average Values',
        })

    markerscale = 1.3-((1-(abs(height)/DEFAULT_HEIGHT))*1.4)
    textscale = 1-((1.3-markerscale)*.4)
    # Create a grouped bar chart
    fig = px.bar( df, x='Facings', y='Average Values',error_y='stddev' if showErrBars else None,
                    barmode='group',  # Use 'group' for grouped bars
                    color='reporting2',
                    color_discrete_map=reporting_palette,
                    labels={'Facings': 'Facings', 'value': 'Average Values'},
                    width=width, height=height)
    applyStandardVBarFormatting(fig, textscale=textscale, nCats=5)

    # If benchmark data passed in, layer that over
    # At the top level, no benchmark will be empty, even if it has no data for some facing
    if(benchmarks!=None) :
        # We add them in reverse order so the most recent is on top
        imarker = min(len(benchmarks), NMARKERSMAX)-1
        while imarker >= 0:
            bm = benchmarks[imarker]
            fig.add_trace(go.Scatter(x=Facing_xvals, y=bm['data'], mode='markers', 
                                        marker_color=barmarkercolors[imarker], marker_line_width=2, marker_line_color='white',
                                        marker_size=MARKER_SZ*markerscale*barmarkerscales[imarker], marker_symbol=vbarmarkertypes[imarker], name=bm['name']))
            imarker-=1
        fig.update_traces(hovertemplate = 'Coverage: %{y:.1f}%<extra></extra>')

    # Convert the figure to HTML including Plotly.js
    return po.to_html(fig, include_plotlyjs=INCLUDE_PLOTLYJS, full_html=True), missing_cats

def facingCapsDataGraphByReporting(answers, facing, topic, benchmarks=None, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT, showErrBars=True):
    #print("facingCapsDataGraphByReporting with: ", answers.count()," answers")
    if (answers.count() == 0): 
        return None
    answers = answers.filter(question__topic__facing__slug=facing)
    answers = answers.annotate(reporting2=Case(
        # Since most old profiles have Null for Reporting, let's map it
        When(assessment__profile__org_chart__isnull=True, then=Value(VALUE_UNKNOWN)),  
        default=F('assessment__profile__org_chart') ))

    # Note that answers has been pre-filtered of domain topic and not_applicable answers
    if topic == 'all':
        answers = answers.order_by('question__topic__index') #, 'reporting2')
        data = answers.aggregate_score('question__topic__slug','reporting2')\
                    .values('question__topic__slug','reporting2','average','stddev')

        df = pd.DataFrame(data)     # Convert the queryset to a DataFrame
        # Map the topic slugs to names
        labelMap, yvalues = labelMapForFacing(facing)
        df['question__topic__slug'] = df['question__topic__slug'].map(labelMap)
    else:
        answers = answers.filter(question__topic__slug=topic).order_by('question__index') #, 'reporting2')
        data = answers.aggregate_score('question__slug','reporting2')\
                    .values('question__slug','reporting2','average','stddev')
        df = pd.DataFrame(data)     # Convert the queryset to a DataFrame
        # Map the topic slugs to names
        labelMap, yvalues = labelMapForTopic(facing, topic)
        df['question__slug'] = df['question__slug'].map(labelMap)

    df['reporting2'] = df['reporting2'].map(reporting_mapping)
    missing_cats = True if df['reporting2'].nunique() < len(reporting_mapping) else False

    # clip values to [0,1] since the collaboration boost/discount can push coverage over 1.0 and under 0
    df['average'] =  df['average'].clip(lower=0.0, upper=1.0)
    # Multiply by 100 to display percentages
    df['average'] *= 100
    df['stddev'] *= 100

    # Rename the columns for clarity
    if topic == 'all':
        df= df.rename(columns={'question__topic__slug' : 'Topics','average':'Average Value',})
        yName = 'Topics'
    else:
        df= df.rename(columns={'question__slug' : 'Questions','average':'Average Value',})
        yName = 'Questions'
    
    #markerscale = (abs(height)/DEFAULT_HEIGHT)
    markerscale = 1-((1-(abs(height)/DEFAULT_HEIGHT))*1.3)
    textscale = 0.9-((1-markerscale)*.3)

    if height <= CALCULATE_SCALED_HEIGHT:
        legendCount = len(reporting_mapping)
        if(benchmarks!=None):
            legendCount = legendCount+len(benchmarks)
        height = calculateScaledHeight(len(yvalues), legendCount, abs(height))
    
    # Create a grouped bar chart
    fig = px.bar(df, y=yName, x='Average Value',error_x='stddev' if showErrBars else None,
                color='reporting2',
                color_discrete_map=reporting_palette,
                barmode='group', # Use 'group' for grouped bars
                width=width, height=height )
    applyStandardHBarFormatting(fig, textscale=textscale, nCats=4)

    # If benchmark data passed in, layer that over
    if(benchmarks!=None) :
        # We add them in reverse order so the most recent is on top
        imarker = min(len(benchmarks), NMARKERSMAX)-1
        while imarker >= 0:
            bm = benchmarks[imarker]
            if bm['hasData']:
                bmName = bm['name']
            else:
                bmName = '<span style="font-style:italic;fill:'+colorPalette['noDataLegendFontColor']+';">'+bm['name']+'</em>'
            fig.add_trace(go.Scatter(y=yvalues, x=bm['data'], mode='markers', 
                                        marker_color=barmarkercolors[imarker], marker_line_width=2, marker_line_color='white',
                                        marker_size=MARKER_SZ*markerscale*barmarkerscales[imarker], marker_symbol=hbarmarkertypes[imarker], 
                                        name=bmName))
            imarker-=1
        fig.update_traces(hovertemplate = 'Coverage: %{x:.1f}%<extra></extra>')

    return po.to_html(fig, include_plotlyjs=INCLUDE_PLOTLYJS, full_html=True), missing_cats

