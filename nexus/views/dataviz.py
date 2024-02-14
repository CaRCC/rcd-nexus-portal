import datetime
import logging
from django.urls import reverse
from django.conf import settings
from django.http import HttpRequest
from django.shortcuts import redirect, render
from nexus.utils.filtertree import *
from nexus.forms.dataviz import *
from nexus.models.rcd_profiles import RCDProfile
from nexus.models.ipeds_classification import IPEDSMixin

logger = logging.getLogger(__name__)

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
    if request.method == "POST":
        posted = DataFilterForm(request.POST)
        if posted.is_valid():
            print("FilterForm valid ",posted.cleaned_data)
        else:
            print("FilterForm not valid!")
        filter_form = DataFilterForm(posted.cleaned_data)   # recreate the form (unbound) so we can control which fields show
    else: 
        filter_form = DataFilterForm()
    filter_form.filtertree(includes=DataFilterForm.CHARTS_INCLUDE_ALL)
    context = {
        "filterform":filter_form,
        "breadcrumbs":{
            "Data Viewer":"dataviz:vizmain",
            "Community Demographics":"dataviz:demographics",
            "Chart Views":"dataviz:demographics_chartviews",
            },
        }
    return render(request, "dataviz/chartviews.html", context)

def data_viz_demographics_scatter(request): 
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
        "breadcrumbs":{
            "Data Viewer":"dataviz:vizmain",
            "Community Demographics":"dataviz:demographics",
            "Scatter Plots":"dataviz:demographics_scatterplots",
            }
        }
    return render(request, "dataviz/scatterplots.html", context)

def data_viz_capsmodeldata(request): 
    if request.method == "POST":
        posted = DataFilterForm(request.POST)
        if posted.is_valid():
            print("FilterForm valid ",posted.cleaned_data)
        else:
            print("FilterForm not valid!")
        filter_form = DataFilterForm(posted.cleaned_data)   # recreate the form (unbound) so we can control which fields show
    else: 
        filter_form = DataFilterForm()
    filter_form.filtertree(includes=DataFilterForm.CAPS_DATA_INCLUDE_ALL)
    context = {
        "filterform":filter_form,
        "breadcrumbs":{
            "Data Viewer":"dataviz:vizmain",
            "Capabilities Model Data":"dataviz:capsmodeldata",
            }
        }
    return render(request, "dataviz/capsmodeldata.html", context)

def data_viz_prioritiessdata(request): 
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
        "breadcrumbs":{
            "Data Viewer":"dataviz:vizmain",
            "Priorities Data":"dataviz:prioritiesdata",
            }
        }
    return render(request, "dataviz/prioritiesdata.html", context)
