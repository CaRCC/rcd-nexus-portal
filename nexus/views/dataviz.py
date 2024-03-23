import datetime
import logging
import urllib.parse
from django.contrib import messages
from django.conf import settings
from django.core.mail import send_mail
from django.http import HttpRequest
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import urlencode
from nexus.utils import cmgraphs, demogcharts
from nexus.forms.dataviz import *
from nexus.models.rcd_profiles import RCDProfile
from nexus.models import CapabilitiesAssessment, CapabilitiesAnswer, CapabilitiesTopic
from nexus.models.ipeds_classification import IPEDSMixin
from nexus.models.facings import Facing
from nexus.views.rcd_profiles import view_roles

logger = logging.getLogger(__name__)

MIN_INSTITUTIONS_TO_GRAPH = 5

def data_viz_main(request):
    context = {
        "breadcrumbs":{
            "Data Viewer":"dataviz:vizmain",
            }
        }
    return render(request, "dataviz/vizmain.html", context)

def data_viz_demographics(request): 
    context = {
        "breadcrumbs":{
            "Data Viewer":"dataviz:vizmain",
            "Community Demographics":"dataviz:demographics",
            }
        }
    return render(request, "dataviz/demographics.html", context)

def data_viz_demographics_maps(request): 
    graph = None
    graphtitle = None
    if request.method == "POST":
        posted = DataFilterForm(request.POST)
        if posted.is_valid():
            print("FilterForm valid ",posted.cleaned_data)
        else:
            print("FilterForm not valid!")
        filter_form = DataFilterForm(posted.cleaned_data)   # recreate the form (unbound) so we can control which fields show
    else: 
        filter_form = DataFilterForm()

    filter_form.filtertree(includes=DataFilterForm.INCLUDE_ALL, excludes={DataFilterForm.REGION, DataFilterForm.EPSCOR, DataFilterForm.RESEARCH_EXP})
    #print("FilterForm.hasViewChoices: "+str(filter_form.hasViewChoices))
    context = {
        "filterform":filter_form,
        "graph":graph,
        "graphtitle":graphtitle,
        "breadcrumbs":{
            "Data Viewer":"dataviz:vizmain",
            "Community Demographics":"dataviz:demographics",
            "Map Views":"dataviz:demographics_mapviews",
            }
        }
    return render(request, "dataviz/mapviews.html", context)


# Rewrite this to be one view per chart type, and add a context variable that selects which type.
# Make the Select use that to show that as selected.
# Add a GO button to the template, and have that fetch the view from the option value. 

FOOTNOTE_NOT_ALL_KNOWN = 'Excludes institutions for which this value is unknown'
def data_viz_demographics_charts(request): 
    graph = None
    graphtitle = None
    footnote = None
    chart = None
    if request.method == "POST":
        posted = DataFilterForm(request.POST)
        if posted.is_valid():
            dict = removeNullDictEntries(posted.cleaned_data)
            qs = urlencode(dict)
            return redirect(reverse('dataviz:demographics_chartviews') + '?'+qs)
        else:
            print("FilterForm not valid!")
            filter_form = DataFilterForm(posted.cleaned_data)   # recreate the form and render that with error message
            chart = posted.cleaned_data.get('chart_views')      # Ensure we handle the chart filtering
    else: 
        if(request.GET) :
            dict = request.GET.dict()
            cleaned_dict = fixMultiSelectDictEntries(dict)
            filter_form = DataFilterForm(cleaned_dict)
            chart = cleaned_dict.get('chart_views')
            pop = cleaned_dict.get('population')
            if(pop == 'contrib'):
                popName = 'Contributors'
            else: 
                popName = 'Users'
            #print( "Cleaned dict: ",cleaned_dict)
            profiles = demogcharts.filterProfiles(cleaned_dict)
            instCount = profiles.count()
            if(instCount < MIN_INSTITUTIONS_TO_GRAPH):
                graph = None
                graphtitle = f'Too Few Institutions ({instCount}) to Chart!'
            else:
                match chart:
                    # Note that sum makes no sense for Charts, and will be hidden/disabled in the template
                    case "cc" :
                        if graph := demogcharts.demographicsChartByCC(profiles) :
                            graphtitle = f'Institutional Classification of {instCount} {popName}'
                    case "mission" :
                        if graph := demogcharts.demographicsChartByMission(profiles) :
                            graphtitle = f'Mission of {instCount} {popName}'
                    case "pub_priv" :
                        graph, totalShown = demogcharts.demographicsChartByPubPriv(profiles)
                        if graph :
                            graphtitle = f'Control (Public/Private) of {totalShown} {popName}'
                            if totalShown != instCount :
                                footnote = FOOTNOTE_NOT_ALL_KNOWN
                    case "epscor" :
                        graph, totalShown = demogcharts.demographicsChartByEPSCoR(profiles)
                        if graph :
                            graphtitle = f'EPSCoR status of {totalShown} {popName}'
                            if totalShown != instCount :
                                footnote = FOOTNOTE_NOT_ALL_KNOWN
                    case "msi" :
                        if graph := demogcharts.demographicsChartByMSI(profiles) :
                            graphtitle = f'Minority-serving status of {instCount} {popName}'
                    case "orgmodel" :
                        if graph := demogcharts.demographicsChartByOrgModel(profiles) :
                            graphtitle = f'Organizational Model of {instCount} {popName}'
                    case "reporting" :
                        if graph := demogcharts.demographicsChartByReporting(profiles) :
                            graphtitle = f'Reporting Structure of {instCount} {popName}'
                    case _ :
                        send_mail(
                                subject="Unrecognized Chart Option: "+chart,
                                message=f"{request.user} tried to view Demographic chart option: {chart}, which is not recognized.",
                                from_email=settings.DEFAULT_FROM_EMAIL,
                                recipient_list=[settings.SUPPORT_EMAIL],
                                fail_silently=False,)
                        messages.error(request, f"Unrecognized Chart Option: {chart}. RCD Nexus Admins have been notified.")

                if graph is None:
                    graphtitle = 'No Data to Chart!'
        else :
            #print( "GET with no params ")
            filter_form = DataFilterForm()
            chart = 'cc'    # Set default chart so Filter tree is adjusted
            profiles = demogcharts.getAllProfiles()
            graphtitle = f'Institutional Classifications for {profiles.count()} Users'
            graph = demogcharts.demographicsChartByCC(profiles)

    filter_form.filtertree(includes=DataFilterForm.CHARTS_INCLUDE_ALL)
    context = {
        "filterform":filter_form,
        "graph":graph,
        "graphtitle":graphtitle,
        "footnote":footnote,
        "chart":chart,
        "breadcrumbs":{
            "Data Viewer":"dataviz:vizmain",
            "Community Demographics":"dataviz:demographics",
            "Chart Views":"dataviz:demographics_chartviews",
            },
        }
    return render(request, "dataviz/chartviews.html", context)

def data_viz_demographics_scatter(request): 
    graph = None
    graphtitle = None
    if request.method == "POST":
        posted = DataFilterForm(request.POST)
        if posted.is_valid():
            dict = removeNullDictEntries(posted.cleaned_data)
            qs = urlencode(dict)
            return redirect(reverse('dataviz:demographics_scatterplots') + '?'+qs)
        else:
            print("FilterForm not valid!")
        filter_form = DataFilterForm(posted.cleaned_data)   # recreate the form (unbound) so we can control which fields show
    else: 
        if(request.GET) :
            dict = request.GET.dict()
            cleaned_dict = fixMultiSelectDictEntries(dict)
            filter_form = DataFilterForm(cleaned_dict)
            #print( "Cleaned dict: ",cleaned_dict)
            # Note we need the answers (not institutions) to group into facings for the scatter graph
            answers, instCount = cmgraphs.filterAssessmentData(cleaned_dict)
            if(instCount < MIN_INSTITUTIONS_TO_GRAPH):
                graph = None
                graphtitle = f'Too Few Institutions ({instCount}) to Chart!'
            elif graph := demogcharts.scatterChart(answers, instCount) :
                graphtitle = f'Scatter Graph of {instCount} Contributors'

            if graph is None:
                graphtitle = 'No Data to Graph!'

        else :
            #print( "GET with no params ")
            filter_form = DataFilterForm()
            answers, instCount = cmgraphs.getAllAnswers()
            graph = demogcharts.scatterChart(answers, instCount)
            graphtitle = f'Scatter Graph of All {instCount} Contributors'

    filter_form.filtertree(includes=DataFilterForm.INCLUDE_ALL_CONTRIBS)
    context = {
        "filterform":filter_form,
        "graph":graph,
        "graphtitle":graphtitle,
        "breadcrumbs":{
            "Data Viewer":"dataviz:vizmain",
            "Community Demographics":"dataviz:demographics",
            "Scatter Plots":"dataviz:demographics_scatterplots",
            }
        }
    return render(request, "dataviz/scatterplots.html", context)

def removeNullDictEntries(dict):
    if dict['resexp_min'] is None:
        del dict['resexp_min']
    if dict['resexp_max'] is None:
        del dict['resexp_max']
    return dict

def fixMultiSelectDictEntries(dict):
    # These are passed as a quoted string so we need to turn them into a list
    dict['cc'] = eval(dict['cc'])
    dict['mission'] = eval(dict['mission'])
    dict['pub_priv'] = eval(dict['pub_priv'])
    dict['region'] = eval(dict['region'])
    dict['size'] = eval(dict['size'])
    dict['epscor'] = eval(dict['epscor'])
    dict['msi'] = eval(dict['msi'])
    dict['year'] = eval(dict['year'])
    # print( "Fixed dict: ",dict)
    return dict

facing_sel_mapping = { "rf":"researcher", "df":"data", "swf":"software", "syf":"systems", "spf":"strategy",}


def getInstAverages(benchmarkAssessment, selFacing):
    # Get the answers of interest (no domain, no not-Applicable)
    allAnswers = benchmarkAssessment.filtered_answers()
    values = []

    if selFacing=='all':
        answersByFacing = allAnswers.group_by_facing()
        # Get the average of all questions in each facing.
        for facing in Facing.objects.all():
            answers = answersByFacing[facing]
            agg = answers.aggregate_score()
            coverage = agg["average"]
            # print(f'getInstAvgs(sum) Facing {facing} avg coverage: {coverage}')
            values.append(coverage*100)   # Convert to percent, since that's what we graph
    else:  
        facing_slug = facing_sel_mapping[selFacing]
        answersByFacingTopic = allAnswers.group_by_facing_topic()
        answersForFacingTopics = answersByFacingTopic[facing_slug]
        # Get the average of all questions in each topic in the specified facing.
        for topic in answersForFacingTopics:
            answers = answersByFacing[topic]
            agg = answers.aggregate_score()
            coverage = agg["average"]
            # print(f'getInstAvgs(facing:{facing_slug}) Topic {topic} avg coverage: {coverage}')
            values.append(coverage*100)   # Convert to percent, since that's what we graph
    return values

def data_viz_capsmodeldata(request): 
    graph = None
    graphtitle = None
    chart = None
    benchmarkInfo = None
    if request.method == "POST":
        posted = DataFilterForm(request.POST)
        if posted.is_valid():
            dict = removeNullDictEntries(posted.cleaned_data)
            qs = urlencode(dict)
            return redirect(reverse('dataviz:capsmodeldata') + '?'+qs)
        else:
            print("FilterForm not valid!")
            filter_form = DataFilterForm(posted.cleaned_data)   # recreate the form and render that with error message
            chart = posted.cleaned_data.get('chart_views')      # Ensure we handle the chart filtering
    else: 
        if(request.GET) :
            dict = request.GET.dict()
            cleaned_dict = fixMultiSelectDictEntries(dict)
            filter_form = DataFilterForm(cleaned_dict)
            chart = cleaned_dict.get('chart_views')
            facing = cleaned_dict.get('facings')
            #print( "Cleaned dict: ",cleaned_dict)
            answers, instCount = cmgraphs.filterAssessmentData(cleaned_dict)
            benchmarkAssessment = None
            benchmarkReq = cleaned_dict.get('benchmark')
            if benchmarkReq == 'True':                            # Note that benchmark option not shows if not authenticated.
                if not request.user.is_authenticated:           # Just for safety
                    messages.info(request, f"You must be logged in to use benchmarking.")
                else:
                    print('Looking for approved assessment...')
                    membership = request.user.rcd_profile_memberships.filter(
                            profile__capabilities_assessment__review_status=CapabilitiesAssessment.ReviewStatusChoices.APPROVED,
                             role__in=view_roles).order_by('-profile__year').first()
                    if membership is None or membership.profile.archived:
                        messages.info(request, f"You must have view rights on an approved assessment to use benchmarking.")
                    else:
                        benchmarkAssessment = membership.profile.capabilities_assessment

            if benchmarkAssessment:
                benchmarkInfo = getInstAverages(benchmarkAssessment, facing)
                print('Benchmark info: ',benchmarkInfo)

            if(instCount < MIN_INSTITUTIONS_TO_GRAPH):
                graph = None
                graphtitle = f'Too Few Institutions ({instCount}) to Graph!'
            else:
                facingname = [item for item in DataFilterForm.FACINGS_CHOICES if item[0] == facing]
                # ignore caps feature for now
                # TODO: add support to overlay the benchmarking data
                # Need to get the authenticated user request.user.is_authenticated and request.user.institutions.first(?)
                # instVales = facingstotals2022.loc[facingstotals2022['Inst']==inst]['2021 Calc'].tolist()
                # if(instVals!=None) :
                #   assert len(instVals) == 5, "showFacingsBarGraph passed bad instVals: "+str(instVals)
                # pass into the graph tools. 
                #   ax.scatter([0,1,2,3,4], instVals, color=[1,0.8,0], s=30, zorder=2, label=instName, **kwargs)
                match chart:
                    case "sum":
                        if facing == 'all':
                            graph = cmgraphs.summaryDataGraph(answers, benchmark=benchmarkInfo)
                        else:
                            graph = cmgraphs.facingSummaryDataGraph(answers, facing, benchmark=benchmarkInfo)
                        if graph : 
                            graphtitle = f'{facingname[0][1]} ({instCount} Institutions)'

                    case "cc" :
                        if facing == 'all':
                            graph = cmgraphs.capsDataGraphByCC(answers, benchmark=benchmarkInfo)
                        else:
                            graph = cmgraphs.facingCapsDataGraphByCC(answers, facing, benchmark=benchmarkInfo)
                        if graph : 
                            graphtitle = f'{facingname[0][1]} by Institutional Classification ({instCount} Institutions)'
                    case "mission" :
                        if facing == 'all':
                            graph = cmgraphs.capsDataGraphByMission(answers, benchmark=benchmarkInfo)
                        else:
                            graph = cmgraphs.facingCapsDataGraphByMission(answers, facing, benchmark=benchmarkInfo)
                        if graph : 
                            graphtitle = f'{facingname[0][1]} by Mission ({instCount} Institutions)'
                    case "pub_priv" :
                        if facing == 'all':
                            graph = cmgraphs.capsDataGraphByPubPriv(answers, benchmark=benchmarkInfo)
                        else:
                            graph = cmgraphs.facingCapsDataGraphByPubPriv(answers, facing, benchmark=benchmarkInfo)
                        if graph : 
                            graphtitle = f'{facingname[0][1]} by Control (Public/Private) ({instCount} Institutions)'
                    case "epscor" :
                        if facing == 'all':
                            graph = cmgraphs.capsDataGraphByEPSCoR(answers, benchmark=benchmarkInfo)
                        else:
                            graph = cmgraphs.facingCapsDataGraphByEPSCoR(answers, facing, benchmark=benchmarkInfo)
                        if graph : 
                            graphtitle = f'{facingname[0][1]} by EPSCoR status ({instCount} Institutions)'
                    case "msi" :
                        if facing == 'all':
                            graph = cmgraphs.capsDataGraphByMSI(answers, benchmark=benchmarkInfo)
                        else:
                            graph = cmgraphs.facingCapsDataGraphByMSI(answers, facing, benchmark=benchmarkInfo)
                        if graph : 
                            graphtitle = f'{facingname[0][1]} by Minority-serving status ({instCount} Institutions)'
                    case "orgmodel" :
                        if facing == 'all':
                            graph = cmgraphs.capsDataGraphByOrgModel(answers, benchmark=benchmarkInfo)
                        else:
                            graph = cmgraphs.facingCapsDataGraphByOrgModel(answers, facing, benchmark=benchmarkInfo)
                        if graph : 
                            graphtitle = f'{facingname[0][1]} by Organizational Model ({instCount} Institutions)'
                    case "reporting" :
                        if facing == 'all':
                            graph = cmgraphs.capsDataGraphByReporting(answers, benchmark=benchmarkInfo)
                        else:
                            graph = cmgraphs.facingCapsDataGraphByReporting(answers, facing, benchmark=benchmarkInfo)
                        if graph : 
                            graphtitle = f'{facingname[0][1]} by Reporting Structure ({instCount} Institutions)'
                    case _ :
                        send_mail(
                                subject="Unrecognized Chart Option: "+chart,
                                message=f"{request.user} tried to view chart option: {chart}, which is not recognized.",
                                from_email=settings.DEFAULT_FROM_EMAIL,
                                recipient_list=[settings.SUPPORT_EMAIL],
                                fail_silently=False,)
                        messages.error(request, f"Unrecognized Chart Option: {chart}. RCD Nexus Admins have been notified.")

                if graph is None:
                    graphtitle = 'No Data to Graph!'
        else :
            #print( "GET with no params ")
            filter_form = DataFilterForm()
            graph, instCount = cmgraphs.allSummaryDataGraph()
            if graph is None:
                graphtitle = 'No Data to Graph!'
            else:
                graphtitle = f'All Data Summary Graph By Facings ({instCount} Institutions)'

    # TODO: This should be changed to be request.user.is_data_contributor once that is implemented. 
    excludes = None if request.user.is_authenticated else DataFilterForm.CAPS_DATA_EXCLUDE_NO_DATA_CONTRIB
    filter_form.filtertree(includes=DataFilterForm.CAPS_DATA_INCLUDE_ALL, excludes=excludes)
    context = {
        "filterform":filter_form,
        "graph":graph,
        "graphtitle":graphtitle,
        "chart":chart,
        "breadcrumbs":{
            "Data Viewer":"dataviz:vizmain",
            "Capabilities Model Data":"dataviz:capsmodeldata",
            }
        }
    return render(request, "dataviz/capsmodeldata.html", context)

def data_viz_prioritiessdata(request): 
    graph = None
    graphtitle = None
    if request.method == "POST":
        posted = DataFilterForm(request.POST)
        if posted.is_valid():
            print("FilterForm valid ",posted.cleaned_data)
        else:
            print("FilterForm not valid!")
        filter_form = DataFilterForm(posted.cleaned_data)   # recreate the form (unbound) so we can control which fields show
    else: 
        filter_form = DataFilterForm()
    filter_form.filtertree(includes=DataFilterForm.INCLUDE_ALL_CONTRIBS)
    context = {
        "filterform":filter_form,
        "graph":graph,
        "graphtitle":graphtitle,
        "breadcrumbs":{
            "Data Viewer":"dataviz:vizmain",
            "Priorities Data":"dataviz:prioritiesdata",
            }
        }
    return render(request, "dataviz/prioritiesdata.html", context)
