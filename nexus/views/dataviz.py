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
from nexus.utils.filtertree import *
from nexus.utils import cmgraphs
from nexus.forms.dataviz import *
from nexus.models.rcd_profiles import RCDProfile
from nexus.models.ipeds_classification import IPEDSMixin

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
    print("FilterForm.hasViewChoices: "+str(filter_form.hasViewChoices))
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
def data_viz_demographics_charts(request): 
    graph = None
    graphtitle = None
    chart = None
    if request.method == "POST":
        posted = DataFilterForm(request.POST)
        if posted.is_valid():
            qs = urlencode(posted.cleaned_data)
            return redirect(reverse('dataviz:demographics_chartviews') + '?'+qs)
        #else:
        #    print("FilterForm not valid!")
        filter_form = DataFilterForm(posted.cleaned_data)   # recreate the form (unbound) so we can control which fields show
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
            institutions, instCount = cmgraphs.filterInstitutions(cleaned_dict)
            if(instCount < MIN_INSTITUTIONS_TO_GRAPH):
                graph = None
                graphtitle = 'Too Few Institutions ('+str(instCount)+') to Chart!'
            else:
                match chart:
                    # Note that sum makes no sense for Charts, and will be hidden/disabled in the template
                    case "cc" :
                        if graph := cmgraphs.demographicsChartByCC(institutions) :
                            graphtitle = f'Carnegie Classification of {instCount} (filtered) {popName}'
                    case "mission" :
                        if graph := cmgraphs.demographicsChartByMission(institutions) :
                            graphtitle = f'Mission of {instCount} (filtered) {popName}'
                    case "pub_priv" :
                        if graph := cmgraphs.demographicsChartByPubPriv(institutions) :
                            graphtitle = f'Control (Public/Private) of {instCount} (filtered) {popName}'
                    case "epscor" :
                        if graph := cmgraphs.demographicsChartByEPSCoR(institutions) :
                            graphtitle = f'EPSCoR status of {instCount} (filtered) {popName}'
                    case "msi" :
                        if graph := cmgraphs.demographicsChartByMSI(institutions) :
                            graphtitle = f'Minority-serving status of {instCount} (filtered) {popName}'
                    case "orgmodel" :
                        if graph := cmgraphs.demographicsChartByOrgModel(institutions) :
                            graphtitle = f'Organizational Model of {instCount} (filtered) {popName}'
                    case "reporting" :
                        if graph := cmgraphs.demographicsChartByReporting(institutions) :
                            graphtitle = f'Reporting Structure of {instCount} (filtered) {popName}'
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
            graphtitle = 'Carnegie Classifications for All Users'
            graph = cmgraphs.demographicsChartByCC(cmgraphs.getAllInstitutions())

    filter_form.filtertree(includes=DataFilterForm.CHARTS_INCLUDE_ALL)
    context = {
        "filterform":filter_form,
        "graph":graph,
        "graphtitle":graphtitle,
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
            "Community Demographics":"dataviz:demographics",
            "Scatter Plots":"dataviz:demographics_scatterplots",
            }
        }
    return render(request, "dataviz/scatterplots.html", context)

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

def data_viz_capsmodeldata(request): 
    graph = None
    graphtitle = None
    chart = None
    if request.method == "POST":
        posted = DataFilterForm(request.POST)
        if posted.is_valid():
            qs = urlencode(posted.cleaned_data)
            return redirect(reverse('dataviz:capsmodeldata') + '?'+qs)
        #else:
        #    print("FilterForm not valid!")
        filter_form = DataFilterForm(posted.cleaned_data)   # recreate the form (unbound) so we can control which fields show
    else: 
        if(request.GET) :
            dict = request.GET.dict()
            cleaned_dict = fixMultiSelectDictEntries(dict)
            filter_form = DataFilterForm(cleaned_dict)
            chart = cleaned_dict.get('chart_views')
            #print( "Cleaned dict: ",cleaned_dict)
            answers, instCount = cmgraphs.filterAssessmentData(cleaned_dict)
            if(instCount < MIN_INSTITUTIONS_TO_GRAPH):
                graph = None
                graphtitle = 'Too Few Institutions ('+str(instCount)+') to Graph!'
            else:
                facing = cleaned_dict.get('facings')
                facingname = [item for item in DataFilterForm.FACINGS_CHOICES if item[0] == facing]
                # ignore caps feature for now
                match chart:
                    case "sum":
                        if facing == 'all':
                            graph = cmgraphs.summaryDataGraph(answers)
                        else:
                            graph = cmgraphs.facingSummaryDataGraph(answers, facing)
                        if graph : 
                            graphtitle = facingname[0][1]+' ('+str(instCount)+' Institutions)'

                    case "cc" :
                        if facing == 'all':
                            graph = cmgraphs.capsDataGraphByCC(answers)
                        else:
                            graph = cmgraphs.facingCapsDataGraphByCC(answers, facing)
                        if graph : 
                            graphtitle = facingname[0][1]+' by Carnegie Classification ('+str(instCount)+' Institutions)'
                    case "mission" :
                        if facing == 'all':
                            graph = cmgraphs.capsDataGraphByMission(answers)
                        else:
                            graph = cmgraphs.facingCapsDataGraphByMission(answers, facing)
                        if graph : 
                            graphtitle = facingname[0][1]+' by Mission ('+str(instCount)+' Institutions)'
                    case "pub_priv" :
                        if facing == 'all':
                            graph = cmgraphs.capsDataGraphByPubPriv(answers)
                        else:
                            graph = cmgraphs.facingCapsDataGraphByPubPriv(answers, facing)
                        if graph : 
                            graphtitle = facingname[0][1]+' by Control (Public/Private) ('+str(instCount)+' Institutions)'
                    case "epscor" :
                        if facing == 'all':
                            graph = cmgraphs.capsDataGraphByEPSCoR(answers)
                        else:
                            graph = cmgraphs.facingCapsDataGraphByEPSCoR(answers, facing)
                        if graph : 
                            graphtitle = facingname[0][1]+' by EPSCoR status ('+str(instCount)+' Institutions)'
                    case "msi" :
                        if facing == 'all':
                            graph = cmgraphs.capsDataGraphByMSI(answers)
                        else:
                            graph = cmgraphs.facingCapsDataGraphByMSI(answers, facing)
                        if graph : 
                            graphtitle = facingname[0][1]+' by Minority-serving status ('+str(instCount)+' Institutions)'
                    case "orgmodel" :
                        if facing == 'all':
                            graph = cmgraphs.capsDataGraphByOrgModel(answers)
                        else:
                            graph = cmgraphs.facingCapsDataGraphByOrgModel(answers, facing)
                        if graph : 
                            graphtitle = facingname[0][1]+' by Organizational Model ('+str(instCount)+' Institutions)'
                    case "reporting" :
                        if facing == 'all':
                            graph = cmgraphs.capsDataGraphByReporting(answers)
                        else:
                            graph = cmgraphs.facingCapsDataGraphByReporting(answers, facing)
                        if graph : 
                            graphtitle = facingname[0][1]+' by Reporting Structure ('+str(instCount)+' Institutions)'
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
            graphtitle = 'All Data Summary Graph By Facings'
            graph = cmgraphs.allSummaryDataGraph()

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
