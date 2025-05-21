import datetime
import logging
import math
import textwrap
import urllib.parse
from django.contrib import messages
from django.conf import settings
from django.core.mail import send_mail
from django.http import HttpRequest
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import urlencode
from django.utils.safestring import mark_safe
from nexus.utils import cmgraphs, demogcharts
from nexus.forms.dataviz import *
from nexus.models.rcd_profiles import RCDProfile
from nexus.models import CapabilitiesAssessment, CapabilitiesAnswer, CapabilitiesTopic, CapabilitiesQuestion
from nexus.models.ipeds_classification import IPEDSMixin
from nexus.models.facings import Facing
from nexus.views.rcd_profiles import view_roles
from django.views.decorators.cache import never_cache

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

def data_viz_demographics_contriblist(request): 
    profiles = demogcharts.getAllProfiles(pop='contrib').filter(institution__list_as_contributor=True)
    institutions = profiles.values_list('institution__name')
    instlist = []
    nInsts = institutions.count()
    nPerCol = math.floor(nInsts/3)
    if (nInsts % 3) == 0:
        col0Max = nPerCol
        col1Max = col0Max+nPerCol
        colmax = col0Max
    elif (nInsts % 3) == 1:
        col0Max = nPerCol
        col1Max = col0Max+nPerCol+1
        colmax = col0Max+1
    else:
        col0Max = nPerCol+1
        col1Max = col0Max*2
        colmax = nPerCol+1

    # print(f'col0Max {col0Max} col1Max: {col1Max} colMax: {colmax}', )


    for inst in institutions:
        instlist.append(inst[0])

    instlist.sort()
    # print(instlist)

    rows = []
    for i in range(colmax):    # Col1 (middle) is always the max
        cols = [""]*3
        if i < col0Max:         # Col0 may have one less than col1
            cols[0] = instlist[i]
        if (i+col0Max) < nInsts:
            cols[1] = instlist[i+col0Max]
            if (i+col1Max) < nInsts:
                cols[2] = instlist[i+col1Max]
        rows.append(cols)

    context = {
        "rows":rows,
        "nInsts":nInsts,
        "breadcrumbs":{
            "Data Viewer":"dataviz:vizmain",
            "Community Demographics":"dataviz:demographics",
            "Contributor List":"dataviz:demographics_contriblist",
            }
        }
    return render(request, "dataviz/contriblist.html", context)

@never_cache
def data_viz_demographics_maps(request): 
    graph = None
    graphtitle = None
    nonDefs = ""
    if request.method == "POST":
        posted = DataFilterForm(request.POST)
        if posted.is_valid():
            dict = removeDefaultDictEntries(removeNullDictEntries(posted.cleaned_data))
            qs = urlencode(dict)
            return redirect(reverse('dataviz:demographics_mapviews') + '?'+qs)
        else:
            print("data_viz_demographics_maps: FilterForm not valid!")
            print(posted.errors)
            print(posted.cleaned_data)
            print(request.POST)
            filter_form = DataFilterForm(posted.cleaned_data)   # recreate the form and render that with error message
    else: 
        if(request.GET) :
            dict = request.GET.dict()
            cleaned_dict = fixMissingDictEntries(fixMultiSelectDictEntries(dict))
            nonDefs = listNonDefaultFilters(cleaned_dict)
            filter_form = DataFilterForm(cleaned_dict)
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
                graphtitle = f'Too Few Institutions ({instCount}) to Map!'
            else :
                grSize = cleaned_dict.get('graph_size')
                match grSize:
                    case "lg":
                        grheight = demogcharts.DEFAULT_PIE_HEIGHT
                        grwidth = cmgraphs.DEFAULT_WIDTH
                        #fontscale = 1
                    case "med":
                        grheight = demogcharts.DEFAULT_PIE_HEIGHT * cmgraphs.GRAPHSIZE_MED_SCALE
                        width_scale = 1-((1-cmgraphs.GRAPHSIZE_MED_SCALE)*.7)
                        grwidth = cmgraphs.DEFAULT_WIDTH * cmgraphs.GRAPHSIZE_MED_SCALE
                        #grwidth = cmgraphs.DEFAULT_WIDTH * width_scale
                        #fontscale = width_scale
                    case "sm":
                        grheight = demogcharts.DEFAULT_PIE_HEIGHT * cmgraphs.GRAPHSIZE_SMALL_SCALE
                        width_scale = 1-((1-cmgraphs.GRAPHSIZE_SMALL_SCALE)*.7)
                        grwidth = cmgraphs.DEFAULT_WIDTH * cmgraphs.GRAPHSIZE_SMALL_SCALE
                        #grwidth = cmgraphs.DEFAULT_WIDTH * width_scale
                        #fontscale = width_scale*1.1
                if graph := demogcharts.demographicsMap(profiles,width=grwidth, height=grheight) :
                    graphtitle = f'Geographic Distribution of {instCount} {popName}'
                else:
                    graphtitle = 'No Data to Graph!'

        else :
            #print( "GET with no params ")
            filter_form = DataFilterForm()
            profiles = demogcharts.getAllProfiles()
            if graph := demogcharts.demographicsMap(profiles) :
                graphtitle = f'Geographic Distribution of {profiles.count()} Users'
            else:
                graphtitle = 'No Data to Chart!'

    filter_form.filtertree(includes=DataFilterForm.INCLUDE_ALL, excludes={DataFilterForm.REGION, DataFilterForm.EPSCOR, DataFilterForm.RESEARCH_EXP})
    #print("FilterForm.hasViewChoices: "+str(filter_form.hasViewChoices))
    context = {
        "filterform":filter_form,
        "graph":graph,
        "graphtitle":graphtitle,
        "nonDefs":nonDefs,
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
@never_cache
def data_viz_demographics_charts(request): 
    graph = None
    graphtitle = None
    footnote = None
    chart = None
    nonDefs = ""
    if request.method == "POST":
        posted = DataFilterForm(request.POST)
        if posted.is_valid():
            dict = removeDefaultDictEntries(removeNullDictEntries(posted.cleaned_data))
            qs = urlencode(dict)
            return redirect(reverse('dataviz:demographics_chartviews') + '?'+qs)
        else:
            print("data_viz_demographics_charts: FilterForm not valid!")
            print(posted.errors)
            print(posted.cleaned_data)
            print(request.POST)
            filter_form = DataFilterForm(posted.cleaned_data)   # recreate the form and render that with error message
            chart = posted.cleaned_data.get('chart_views')      # Ensure we handle the chart filtering
    else: 
        if(request.GET) :
            dict = request.GET.dict()
            cleaned_dict = fixMissingDictEntries(fixMultiSelectDictEntries(dict))
            #print( "Cleaned dict: ",cleaned_dict)
            nonDefs = listNonDefaultFilters(cleaned_dict)
            #print( "Non default choices: ",nonDefs)
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
                grSize = cleaned_dict.get('graph_size')
                match grSize:
                    case "lg":
                        grheight = demogcharts.DEFAULT_PIE_HEIGHT
                    case "med":
                        grheight = demogcharts.DEFAULT_PIE_HEIGHT * cmgraphs.GRAPHSIZE_MED_SCALE
                    case "sm":
                        grheight = demogcharts.DEFAULT_PIE_HEIGHT * cmgraphs.GRAPHSIZE_SMALL_SCALE

                match chart:
                    # Note that sum makes no sense for Charts, and will be hidden/disabled in the template
                    case "cc" :
                        if graph := demogcharts.demographicsChartByCC(profiles, height=grheight) :
                            graphtitle = f'Institutional Classification of {instCount} {popName}'
                    case "mission" :
                        if graph := demogcharts.demographicsChartByMission(profiles, height=grheight) :
                            graphtitle = f'Mission of {instCount} {popName}'
                    case "pub_priv" :
                        graph, totalShown = demogcharts.demographicsChartByPubPriv(profiles, height=grheight)
                        if graph :
                            graphtitle = f'Control (Public/Private) of {totalShown} {popName}'
                            if totalShown != instCount :
                                footnote = FOOTNOTE_NOT_ALL_KNOWN
                    case "epscor" :
                        graph, totalShown = demogcharts.demographicsChartByEPSCoR(profiles, height=grheight)
                        if graph :
                            graphtitle = f'EPSCoR status of {totalShown} {popName}'
                            if totalShown != instCount :
                                footnote = FOOTNOTE_NOT_ALL_KNOWN
                    case "msi" :
                        if graph := demogcharts.demographicsChartByMSI(profiles, height=grheight) :
                            graphtitle = f'Minority-serving status of {instCount} {popName}'
                    case "orgmodel" :
                        if graph := demogcharts.demographicsChartByOrgModel(profiles, height=grheight) :
                            graphtitle = f'Organizational Model of {instCount} {popName}'
                    case "reporting" :
                        if graph := demogcharts.demographicsChartByReporting(profiles, height=grheight) :
                            graphtitle = f'Reporting Structure of {instCount} {popName}'
                    case _ :
                        send_mail(
                                subject="Unrecognized Chart Option: "+chart,
                                message=f"{request.user} tried to view Demographic chart option: {chart}, which is not recognized.",
                                from_email=settings.DEFAULT_FROM_EMAIL_USER+'@'+request.get_host(),
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
        "nonDefs":nonDefs,
        "breadcrumbs":{
            "Data Viewer":"dataviz:vizmain",
            "Community Demographics":"dataviz:demographics",
            "Chart Views":"dataviz:demographics_chartviews",
            },
        }
    return render(request, "dataviz/chartviews.html", context)

@never_cache
def data_viz_demographics_scatter(request): 
    graph = None
    graphtitle = None
    nonDefs = ""
    if request.method == "POST":
        posted = DataFilterForm(request.POST)
        if posted.is_valid():
            dict = removeDefaultDictEntries(removeNullDictEntries(posted.cleaned_data))
            qs = urlencode(dict)
            return redirect(reverse('dataviz:demographics_scatterplots') + '?'+qs)
        else:
            print("data_viz_demographics_scatter: FilterForm not valid!")
            print(posted.errors)
            print(posted.cleaned_data)
            print(request.POST)
            filter_form = DataFilterForm(posted.cleaned_data)   # recreate the form (unbound) so we can control which fields show
    else: 
        if(request.GET) :
            dict = request.GET.dict()
            cleaned_dict = fixMissingDictEntries(fixMultiSelectDictEntries(dict))
            nonDefs = listNonDefaultFilters(cleaned_dict)
            #print( "Non default choices: ",nonDefs)
            filter_form = DataFilterForm(cleaned_dict)
            #print( "Cleaned dict: ",cleaned_dict)
            # Note we need the answers (not institutions) to group into facings for the scatter graph
            answers, instCount = cmgraphs.filterAssessmentData(cleaned_dict)
            if(instCount < MIN_INSTITUTIONS_TO_GRAPH):
                graph = None
                graphtitle = f'Too Few Institutions ({instCount}) to Chart!'
            else :
                grSize = cleaned_dict.get('graph_size')
                match grSize:
                    case "lg":
                        grheight = demogcharts.DEFAULT_SCATTER_HEIGHT
                        grwidth = cmgraphs.DEFAULT_WIDTH
                        fontscale = 1
                    case "med":
                        grheight = demogcharts.DEFAULT_SCATTER_HEIGHT * cmgraphs.GRAPHSIZE_MED_SCALE
                        width_scale = 1-((1-cmgraphs.GRAPHSIZE_MED_SCALE)*.7)
                        grwidth = cmgraphs.DEFAULT_WIDTH * width_scale
                        fontscale = width_scale
                    case "sm":
                        grheight = demogcharts.DEFAULT_SCATTER_HEIGHT * cmgraphs.GRAPHSIZE_SMALL_SCALE
                        width_scale = 1-((1-cmgraphs.GRAPHSIZE_SMALL_SCALE)*.7)
                        grwidth = cmgraphs.DEFAULT_WIDTH * width_scale
                        fontscale = width_scale*1.1
                if graph := demogcharts.scatterChart(answers, instCount, height=grheight, width=grwidth, fontscale=fontscale) :
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
        "nonDefs":nonDefs,
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

def removeDefaultDictEntries(dict):
    if dict.get('population') == 'all':
        del dict['population']
    if dict.get('chart_views') == 'sum':
        del dict['chart_views']
    if dict.get('facings') == 'all':
        del dict['facings']
    if dict.get('topics') == 'all':
        del dict['topics']
    if cc := dict.get('cc'):
        if len(cc) == len(DataFilterForm.CC_CHOICES):
            del dict['cc']
    if eps := dict.get('epscor'):
        if len(eps) == len(DataFilterForm.EPSCOR_CHOICES):
            del dict['epscor']
    if missions := dict.get('mission'):
        if len(missions) == len(DataFilterForm.MISSION_CHOICES):
            del dict['mission']
    if pp := dict.get('pub_priv'):
        if len(pp) == len(DataFilterForm.PUB_PRIV_CHOICES):
            del dict['pub_priv']
    if msis := dict.get('msi'):
        if len(msis) == len(DataFilterForm.MSI_CHOICES):
            del dict['msi']
    if sizes := dict.get('size'):
        if len(sizes) == len(DataFilterForm.SIZE_CHOICES):
            del dict['size']
    if regions := dict.get('region'):
        if len(regions) == len(DataFilterForm.REGION_CHOICES):
            del dict['region']
    if years := dict.get('year'):
        if len(years) == len(DataFilterForm.YEAR_CHOICES):
            del dict['year']
    if dict.get('benchmark') == False:
        del dict['benchmark']
    if dict.get('graph_size') == 'lg':
        del dict['graph_size']
    if dict.get('opt_show_errbars') == True:
        del dict['opt_show_errbars']
    if dict.get('caps_feature') == 'cov':
        del dict['caps_feature']

    return dict

def fixMissingDictEntries(dict):
    if dict.get('population') == None:
        dict['population'] = 'all'
    if dict.get('chart_views') == None:
        dict['chart_views'] = 'sum'
    if dict.get('facings') == None:
        dict['facings'] = 'all'
    if dict.get('topics') == None:
        dict['topics'] = 'all'
    if dict.get('caps_feature') == None:
        dict['caps_feature'] = 'cov'
    if dict.get('benchmark') == None:
        dict['benchmark'] = False
    if dict.get('graph_size') == None:
        dict['graph_size'] = 'lg'
    if dict.get('opt_show_errbars') == None:
        dict['opt_show_errbars'] = True
    return dict

def listNonDefaultFilters(dict):
    list = []
    prefix = 'id_'
    suffix = '_d'
    if dict.get('population') != None and dict.get('population') == 'contrib':
        list.append(prefix+'population'+suffix)
    if dict.get('cc') != None and dict.get('cc') != [c[0] for c in DataFilterForm.CC_CHOICES]:
        list.append(prefix+'cc'+suffix)
    if dict.get('epscor') != None and dict.get('epscor') != [str(c[0]) for c in DataFilterForm.EPSCOR_CHOICES]:
        list.append(prefix+'epscor'+suffix)
    if dict.get('mission') != None and dict.get('mission') != [c[0] for c in DataFilterForm.MISSION_CHOICES]:
        list.append(prefix+'mission'+suffix)
    if dict.get('pub_priv') != None and dict.get('pub_priv') != [c[0] for c in DataFilterForm.PUB_PRIV_CHOICES]:
        list.append(prefix+'pub_priv'+suffix)
    if dict.get('region') != None and dict.get('region') != [str(c[0]) for c in DataFilterForm.REGION_CHOICES]:
        list.append(prefix+'region'+suffix)
    if dict.get('size') != None and dict.get('size') != [str(c[0]) for c in DataFilterForm.SIZE_CHOICES]:
        list.append(prefix+'size'+suffix)
    if dict.get('msi') != None and dict.get('msi') != [c[0] for c in DataFilterForm.MSI_CHOICES]:
        list.append(prefix+'msi'+suffix)
    if dict.get('year') != None and dict.get('year') != [str(c[0]) for c in DataFilterForm.YEAR_CHOICES]:
        list.append(prefix+'year'+suffix)
    return ';'.join(list)

def fixMultiSelectDictEntries(dict):
    # These are passed as a quoted string so we need to turn them into a list
    if 'cc' in dict:
        dict['cc'] = eval(dict['cc'])
    else:
        dict['cc'] = [c[0] for c in DataFilterForm.CC_CHOICES]
    
    if 'mission' in dict:
        dict['mission'] = eval(dict['mission'])
    else: 
        dict['mission'] = [c[0] for c in DataFilterForm.MISSION_CHOICES]
    
    if 'pub_priv' in dict:
        dict['pub_priv'] = eval(dict['pub_priv'])
    else: 
        dict['pub_priv'] = [c[0] for c in DataFilterForm.PUB_PRIV_CHOICES]
    
    if 'region' in dict:
        dict['region'] = eval(dict['region'])
    else: 
        dict['region'] = [str(c[0]) for c in DataFilterForm.REGION_CHOICES]
    
    if 'size' in dict:
        dict['size'] = eval(dict['size'])
    else: 
        dict['size'] = [str(c[0]) for c in DataFilterForm.SIZE_CHOICES]

    if 'epscor' in dict:
        dict['epscor'] = eval(dict['epscor'])
    else: 
        dict['epscor'] = [str(c[0]) for c in DataFilterForm.EPSCOR_CHOICES]

    if 'msi' in dict:
        dict['msi'] = eval(dict['msi'])
    else: 
        dict['msi'] = [c[0] for c in DataFilterForm.MSI_CHOICES]
    if 'year' in dict:
        dict['year'] = eval(dict['year'])
    else: 
        dict['year'] = [str(c[0]) for c in DataFilterForm.YEAR_CHOICES]
    # print( "Fixed dict: ",dict)
    return dict

facing_sel_mapping = { "rf":"researcher", "df":"data", "swf":"software", "syf":"systems", "spf":"strategy",}


def getInstAverages(benchmarkAssessment, facingslug, topicslug='all', bmQuestions=None):
    # Get the answers of interest (no domain, no not-Applicable)
    allAnswers = benchmarkAssessment.filtered_answers().annotate_coverage()
    if bmQuestions != None:
        allAnswers = allAnswers.filter(question__id__in=bmQuestions)
    values = []

    if facingslug=='all':
        answersByFacing = allAnswers.group_by_facing()
        # Get the average of all questions in each facing.
        for facing in Facing.objects.all():
            # For the sparse facings, we need to filter to just the questions that were answered
            if facing in answersByFacing:
                answers = answersByFacing[facing]
                agg = answers.aggregate_score()
                coverage = agg["average"]
                coverage = min(1.0, max(0.0, coverage))
                # print(f'getInstAvgs(sum) Facing {facing} avg coverage: {coverage}')
                values.append(coverage*100)   # Convert to percent, since that's what we graph
            else: # No data for this facing
                values.append(None)
        return values, allAnswers, True # For all facings, there must be at least one data point
    
    facing = Facing.objects.get(slug=facingslug) 

    if topicslug=='all': # Specified facing, all topics
        answersForFacingTopic = dict()
        allAnswers = allAnswers.filter(question__topic__facing=facing)
        for topic in facing.capmodel_topics.all():
            answers = allAnswers.filter(question__topic=topic)
            if answers:
                answersForFacingTopic[topic] = answers.order_by("question__index")

        # Get the average of all questions in each topic in the specified facing.
        hasData = False # Assume no data until we see some
        for topic in facing.capmodel_topics.all(): # review all topics in the facing, not just those with answers
            if topic in answersForFacingTopic:
                answers = answersForFacingTopic[topic]
                agg = answers.aggregate_score()
                coverage = agg["average"]
                coverage = min(1.0, max(0.0, coverage))
                # print(f'getInstAvgs(facing:{facing_slug}) Topic {topic} avg coverage: {coverage}')
                values.append(coverage*100)   # Convert to percent, since that's what we graph
                hasData = True
            else: # No data for this topic
                values.append(None)
        return values, allAnswers, hasData
    
    # else: Specified facing, Specified topic
    #print(f'getInstAvgs(facing:{facingslug}) Topic {topicslug}')

    topic = CapabilitiesTopic.objects.filter(facing=facing).get(slug=topicslug) 

    facingTopicAnswers = allAnswers.filter(question__topic__facing=facing).filter(question__topic=topic).order_by("question__index")
    answersForFacingTopicQuestions = dict((a.question.slug, a) for a in facingTopicAnswers)
    #print(f'Have bm answers for: {answersForFacingTopicQuestions.keys()}')

    # Get the coverage of each question in the specified topic in the specified facing.
    allFacingTopicQuestions = CapabilitiesQuestion.objects.all().filter(topic__facing=facing).filter(topic=topic).order_by("index")
    #print(f'Have questions for: {allFacingTopicQuestions.values("slug")}')
    hasData = False # Assume no data until we see some
    for q in allFacingTopicQuestions: # review all questions in the facing and topic, not just those with answers
        if q.slug in answersForFacingTopicQuestions:
            answer = answersForFacingTopicQuestions[q.slug]
            coverage = min(1.0, max(0.0, answer.coverage))
            # print(f'getInstAvgs(facing:{facingslug}) Topic {topic} Question {q.slug} coverage: {coverage}')
            values.append(coverage*100)   # Convert to percent, since that's what we graph
            hasData = True
        else: # No data for this question
            values.append(None)
    return values, facingTopicAnswers, hasData


@never_cache
def data_viz_capsmodeldata(request): 
    graph = None
    graphtitle = None
    chart = None
    benchmarkInfo = None
    showErrBars = False
    multiBenchMarkNote = None
    partialBenchMarkNote = None
    missingBenchmarkDataNote = None
    missing_cats = False    # when filters results in partial data for compare-by graphs
    nonDefs = ""
    printQsAnchor = None
    if request.method == "POST":
        posted = DataFilterForm(request.POST)
        if posted.is_valid():
            dict = removeDefaultDictEntries(removeNullDictEntries(posted.cleaned_data))
            qs = urlencode(dict)
            return redirect(reverse('dataviz:capsmodeldata') + '?'+qs)
        else:
            print("data_viz_capsmodeldata: FilterForm not valid!")
            print(posted.errors)
            print(posted.cleaned_data)
            # print(request.POST)
            filter_form = DataFilterForm(posted.cleaned_data)   # recreate the form and render that with error message
            chart = posted.cleaned_data.get('chart_views')      # Ensure we handle the chart filtering
    else: 
        if(request.GET) :
            dict = request.GET.dict()
            cleaned_dict = fixMissingDictEntries(fixMultiSelectDictEntries(dict))
            nonDefs = listNonDefaultFilters(cleaned_dict)
            # print( "Non default choices: ",nonDefs)
            filter_form = DataFilterForm(cleaned_dict)
            chart = cleaned_dict.get('chart_views')
            facing = cleaned_dict.get('facings')
            if facing == 'all':
                facingslug = facing
            else:
                facingslug = facing_sel_mapping.get(facing)
            topic = cleaned_dict.get('topics')
            if topic == 'all':
                topicslug = topic
            else:
                topicslug = topic[topic.find("_")+1:]
            #print( "Cleaned dict: ",cleaned_dict)
            basisBenchmarkQuestionIDs = None
            basisBenchmarkYear = None
            benchmarkReq = cleaned_dict.get('benchmark')
            if benchmarkReq == 'True':                            # Note that benchmark option not shows if not authenticated.
                if not request.user.is_authenticated:           # Just for safety
                    messages.info(request, f"You must be logged in to use benchmarking.")
                else:
                    # print('Looking for approved assessment...')
                    # Allow them to benchmark up to 3 assessments. If this is really a problem, they can go archive some to see the ones they want. 
                    bmProfiles = RCDProfile.objects.filter_can_view(request.user).exclude(archived=True)\
                        .filter(capabilities_assessment__review_status=CapabilitiesAssessment.ReviewStatusChoices.APPROVED)\
                        .order_by('-year', '-capabilities_assessment__update_time')[:3]
                    if not bmProfiles:
                        messages.info(request, f"You must have view rights on an approved assessment to use benchmarking.")
                    else:
                        benchmarkInfo = []
                        for bmprof in bmProfiles:
                            benchmarkAssessment = bmprof.capabilities_assessment

                            firstBMSuffix = ''
                            if basisBenchmarkQuestionIDs == None:    # First in list is the newest
                                data, bmAnswers, hasData = getInstAverages(benchmarkAssessment, facingslug, topicslug)
                                basisBenchmarkQuestionIDs = bmAnswers.values('question__id')
                                basisBenchmarkYear = bmprof.year
                                if bmProfiles.count()>1:
                                    firstBMSuffix = '*'
                                    multiBenchMarkNote = mark_safe("<b>*</b> indicates the basis benchmarking assessment.")
                            else:
                                data, bmAnswers, hasData = getInstAverages(benchmarkAssessment, facingslug, topicslug, bmQuestions=basisBenchmarkQuestionIDs)
                            # Name shortener 
                            # 1) Split off the suffix in parens (the type and year)
                            # 2) Shorten the root to 20
                            # 3) Join the results of the two with a break tag, and indent the suffix with &nbsp; chars
                            profName = str(bmprof)
                            sliceIndex = profName.rindex('(')
                            baseName = textwrap.shorten(profName[:sliceIndex], width=20, placeholder="...")
                            suffix = '&nbsp;&nbsp;'+profName[sliceIndex:]
                            bmName = '<b>'+baseName+'<br>'+suffix+firstBMSuffix+'</b>'
                            #print('First Benchmark questions: ',str(basisBenchmarkQuestions))
                            #print('Adding Benchmark info for: ',bmName)
                            benchmarkInfo.append({ 'data':data, 'hasData':hasData, 'name':bmName })
                            if not hasData: 
                                missingBenchmarkDataNote = \
                                    mark_safe('<span class="missing">Shaded italics</span> in the legend indicates a benchmarking assessment that has no data for this view.')
                            

            # Filter for the institutional filters, but not on facing or topic
            answers, instCount = cmgraphs.filterAssessmentData(cleaned_dict, bmQuestions=basisBenchmarkQuestionIDs)
            # Now filter for the view choices
            graphtitle = None
            if instCount < MIN_INSTITUTIONS_TO_GRAPH:
                graphtitle = f'Too Few Institutions ({instCount}) to Graph!'
            if facing != 'all':
                if topic == 'all':
                    answers = answers.filter(question__topic__facing__slug=facingslug)
                    if not answers.exists():
                        graphtitle = f'Benchmark basis assessment included no questions in this Facing.'
                else: 
                    answers = answers.filter(question__topic__facing__slug=facingslug).filter(question__topic__slug=topicslug)
                    if not answers.exists():
                        graphtitle = f'Benchmark basis assessment included no questions in this Topic.'

            if graphtitle != None:
                graph = None
            else:
                facingname = [item for item in DataFilterForm.FACINGS_CHOICES if item[0] == facing]

                if basisBenchmarkYear != None:  # we're doing benchmarking - check the counts for that year
                    fullQuestionCountForBasisYear = CapabilitiesQuestion.getQuestionCount(basisBenchmarkYear, forFacing=facingslug, forTopic=topicslug)
                    if basisBenchmarkQuestionIDs.count() < fullQuestionCountForBasisYear:
                        if facing == 'all':
                            topicQualifier = '' 
                        elif topic == 'all':
                            topicQualifier = 'in this facing '
                        else:
                            topicQualifier = 'in this topic '
                        partialBenchMarkNote = mark_safe(f'The basis benchmark assessment includes {basisBenchmarkQuestionIDs.count()} questions of {fullQuestionCountForBasisYear} {topicQualifier}for {basisBenchmarkYear}, and community data has been filtered accoundingly.')
                    #else:
                        #print(f'Basis benchmark assessment has all {basisBenchmarkQuestionIDs.count()} questions of {fullQuestionCountForBasisYear} for {basisBenchmarkYear} (topicQualifier}.')

                grSize = cleaned_dict.get('graph_size')
                match grSize:
                    case "lg":
                        grheight = cmgraphs.DEFAULT_HEIGHT
                        grwidth = cmgraphs.DEFAULT_WIDTH
                        grwidth2 = grwidth
                    case "med":
                        grheight = cmgraphs.DEFAULT_HEIGHT * cmgraphs.GRAPHSIZE_MED_SCALE
                        if benchmarkInfo :
                            grwidth = cmgraphs.DEFAULT_WIDTH * (1-((1-cmgraphs.GRAPHSIZE_MED_SCALE)*.7))
                            grwidth2 = cmgraphs.DEFAULT_WIDTH * (1-((1-cmgraphs.GRAPHSIZE_MED_SCALE)*.6))
                        else:
                            grwidth = cmgraphs.DEFAULT_WIDTH * cmgraphs.GRAPHSIZE_MED_SCALE
                            grwidth2 = cmgraphs.DEFAULT_WIDTH * (1-((1-cmgraphs.GRAPHSIZE_MED_SCALE)*.7))
                    case "sm":
                        grheight = cmgraphs.DEFAULT_HEIGHT * (1-((1-cmgraphs.GRAPHSIZE_SMALL_SCALE)*.8))
                        if benchmarkInfo :
                            grwidth = cmgraphs.DEFAULT_WIDTH * (1-((1-cmgraphs.GRAPHSIZE_SMALL_SCALE)*.7))
                            grwidth2 = cmgraphs.DEFAULT_WIDTH * (1-((1-cmgraphs.GRAPHSIZE_SMALL_SCALE)*.6))
                        else:
                            grwidth = cmgraphs.DEFAULT_WIDTH * cmgraphs.GRAPHSIZE_SMALL_SCALE
                            grwidth2 = cmgraphs.DEFAULT_WIDTH * (1-((1-cmgraphs.GRAPHSIZE_SMALL_SCALE)*.7))

                if facing != 'all':
                    grheight *= cmgraphs.CALCULATE_SCALED_HEIGHT
                    printQsAnchor = facing+'topics'
                    if topic == 'all':
                        printQsAnchor = facing+'topics'
                    else:
                        printQsAnchor = facing+topicslug+'_qs'

                showErrBars = cleaned_dict.get('opt_show_errbars') != 'False'
                # print("ShowErrBars: ",showErrBars)

                if facing == 'all' or topic == 'all':
                    graphPrefix = f'{facingname[0][1]}'
                else: # Chosen facing and topic
                    graphPrefix = f'{facingname[0][1][:-7]}: {cmgraphs.labelForFacingTopic(facingslug, topicslug)} Questions<br>'

                match chart:
                    case "sum":
                        if facing == 'all':
                            # Scale the size slightly since the summary graph has no legend
                            graph = cmgraphs.summaryDataGraph(answers, benchmarks=benchmarkInfo,
                                                              height=grheight*.9, width=grwidth*.9, showErrBars=showErrBars)
                        elif topic == 'all':
                            graph = cmgraphs.facingSummaryDataGraph(answers, facingslug, benchmarks=benchmarkInfo, 
                                                                    height=grheight, width=grwidth, showErrBars=showErrBars)
                        else: # topic specified
                            graph = cmgraphs.topicSummaryDataGraph(answers, facingslug, topicslug, benchmarks=benchmarkInfo, 
                                                                    height=grheight, width=grwidth, showErrBars=showErrBars)
                        if graph : 
                            graphtitle = f'{graphPrefix} ({instCount} Institutions)'

                    case "cc" :
                        if facing == 'all':
                            graph, missing_cats = cmgraphs.capsDataGraphByCC(answers, benchmarks=benchmarkInfo, height=grheight, width=grwidth, showErrBars=showErrBars)
                        else:
                            graph, missing_cats = cmgraphs.facingCapsDataGraphByCC(answers, facingslug, topicslug, benchmarks=benchmarkInfo, 
                                                                     height=grheight, width=grwidth2, showErrBars=showErrBars)
                        if graph : 
                            graphtitle = f'{graphPrefix} by Institutional Classification ({instCount} Institutions)'
                    case "mission" :
                        if facing == 'all':
                            graph, missing_cats = cmgraphs.capsDataGraphByMission(answers, benchmarks=benchmarkInfo, height=grheight, width=grwidth, showErrBars=showErrBars)
                        else:
                            graph, missing_cats = cmgraphs.facingCapsDataGraphByMission(answers, facingslug, topicslug, benchmarks=benchmarkInfo, 
                                                                          height=grheight, width=grwidth2, showErrBars=showErrBars)
                        if graph : 
                            graphtitle = f'{graphPrefix} by Mission ({instCount} Institutions)'
                    case "pub_priv" :
                        if facing == 'all':
                            graph, missing_cats = cmgraphs.capsDataGraphByPubPriv(answers, benchmarks=benchmarkInfo, height=grheight, width=grwidth, showErrBars=showErrBars)
                        else:
                            graph, missing_cats = cmgraphs.facingCapsDataGraphByPubPriv(answers, facingslug, topicslug, benchmarks=benchmarkInfo, 
                                                                          height=grheight, width=grwidth, showErrBars=showErrBars)
                        if graph : 
                            graphtitle = f'{graphPrefix} by Control (Public/Private) ({instCount} Institutions)'
                    case "epscor" :
                        if facing == 'all':
                            graph, missing_cats = cmgraphs.capsDataGraphByEPSCoR(answers, benchmarks=benchmarkInfo, height=grheight, width=grwidth, showErrBars=showErrBars)
                        else:
                            graph, missing_cats = cmgraphs.facingCapsDataGraphByEPSCoR(answers, facingslug, topicslug, benchmarks=benchmarkInfo, 
                                                                         height=grheight, width=grwidth2, showErrBars=showErrBars)
                        if graph : 
                            graphtitle = f'{graphPrefix} by EPSCoR status ({instCount} Institutions)'
                    case "msi" :
                        if facing == 'all':
                            graph, missing_cats = cmgraphs.capsDataGraphByMSI(answers, benchmarks=benchmarkInfo, height=grheight, width=grwidth, showErrBars=showErrBars)
                        else:
                            graph, missing_cats = cmgraphs.facingCapsDataGraphByMSI(answers, facingslug, topicslug, benchmarks=benchmarkInfo, 
                                                                      height=grheight, width=grwidth2, showErrBars=showErrBars)
                        if graph : 
                            graphtitle = f'{graphPrefix} by Minority-serving status ({instCount} Institutions)'
                    case "orgmodel" :
                        if facing == 'all':
                            graph, missing_cats = cmgraphs.capsDataGraphByOrgModel(answers, benchmarks=benchmarkInfo, height=grheight, width=grwidth2, showErrBars=showErrBars)
                        else:
                            graph, missing_cats = cmgraphs.facingCapsDataGraphByOrgModel(answers, facingslug, topicslug, benchmarks=benchmarkInfo, 
                                                                           height=grheight, width=grwidth2, showErrBars=showErrBars)
                        if graph : 
                            graphtitle = f'{graphPrefix} by Organizational Model ({instCount} Institutions)'
                    case "reporting" :
                        if facing == 'all':
                            graph, missing_cats = cmgraphs.capsDataGraphByReporting(answers, benchmarks=benchmarkInfo, height=grheight, width=grwidth2, showErrBars=showErrBars)
                        else:
                            graph, missing_cats = cmgraphs.facingCapsDataGraphByReporting(answers, facingslug, topicslug, benchmarks=benchmarkInfo, 
                                                                            height=grheight, width=grwidth2, showErrBars=showErrBars)
                        if graph : 
                            graphtitle = f'{graphPrefix} by Reporting Structure ({instCount} Institutions)'
                    case _ :
                        send_mail(
                                subject="Unrecognized Chart Option: "+chart,
                                message=f"{request.user} tried to view chart option: {chart}, which is not recognized.",
                                from_email=settings.DEFAULT_FROM_EMAIL_USER+'@'+request.get_host(),
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

    excludes = None if (request.user.is_authenticated and request.user.is_capmodel_contributor) else DataFilterForm.CAPS_DATA_EXCLUDE_NO_DATA_CONTRIB
    filter_form.filtertree(includes=DataFilterForm.CAPS_DATA_INCLUDE_ALL, excludes=excludes)
    context = {
        "filterform":filter_form,
        "graph":graph,
        "graphtitle":graphtitle,
        "chart":chart,
        "showErrBars":showErrBars,
        "multiBenchMarkNote":multiBenchMarkNote,
        "missingBenchmarkDataNote":missingBenchmarkDataNote,
        "partialBenchMarkNote":partialBenchMarkNote,
        "missingCats":missing_cats,
        "printQsAnchor":printQsAnchor,
        "nonDefs":nonDefs,
        "breadcrumbs":{
            "Data Viewer":"dataviz:vizmain",
            "Capabilities Model Data":"dataviz:capsmodeldata",
            }
        }
    return render(request, "dataviz/capsmodeldata.html", context)

def data_viz_prioritiessdata(request): 
    graph = None
    graphtitle = None
    nonDefs = ""
    if request.method == "POST":
        posted = DataFilterForm(request.POST)
        if posted.is_valid():
            dict = removeDefaultDictEntries(removeNullDictEntries(posted.cleaned_data))
            qs = urlencode(dict)
            return redirect(reverse('dataviz:prioritiesdata') + '?'+qs)
        else:
            print("data_viz_prioritiessdata: FilterForm not valid!")
            print(posted.errors)
            print(posted.cleaned_data)
            print(request.POST)
            filter_form = DataFilterForm(posted.cleaned_data)   # recreate the form (unbound) so we can control which fields show
    else: 
        if(request.GET) :
            dict = request.GET.dict()
            cleaned_dict = fixMissingDictEntries(fixMultiSelectDictEntries(dict))
            nonDefs = listNonDefaultFilters(cleaned_dict)
            filter_form = DataFilterForm(cleaned_dict)
            #print( "Cleaned dict: ",cleaned_dict)
            # This is where we would generate the graph
            graphtitle = 'Priorities Graphing is not yet implemented'
        else :
            #print( "GET with no params ")
            filter_form = DataFilterForm()
            graphtitle = 'Priorities Graphing is not yet implemented'

    filter_form.filtertree(includes=DataFilterForm.INCLUDE_ALL_CONTRIBS)
    context = {
        "filterform":filter_form,
        "graph":graph,
        "graphtitle":graphtitle,
        "nonDefs":nonDefs,
        "breadcrumbs":{
            "Data Viewer":"dataviz:vizmain",
            "Priorities Data":"dataviz:prioritiesdata",
            }
        }
    return render(request, "dataviz/prioritiesdata.html", context)

