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

# At some point may need to put these into a fixture to handle translations
POPULATION="Population"
POP_ALL="All Users"
POP_CONTRIB="Contributors"
CARN_CLASS="Carnegie Class."
MISSION="Mission"
PUB_PRIV="Public/Private"
PUB_PRIV_PUBLIC="Public"
PUB_PRIV_PRIVATE="Private"
EPSCOR="EPSCoR"
MSI="Minority Serving"
MSI_NOT="Not Minority Serving"
MSI_HBCU="HBCU"
MSI_HSI="HSI"
MSI_OTHER="Other MSI"
SIZE="Size"
BY_YEAR="By Year"
REGION="Region"
RESEARCH_EXP="Research Exp."

INCLUDE_ALL={POPULATION, CARN_CLASS, MISSION, PUB_PRIV, EPSCOR, MSI, SIZE, BY_YEAR, REGION, RESEARCH_EXP}
INCLUDE_ALL_CONTRIBS={CARN_CLASS, MISSION, PUB_PRIV, EPSCOR, MSI, SIZE, BY_YEAR, REGION, RESEARCH_EXP}

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

    filter_form.filtertree(excludes={REGION, EPSCOR, RESEARCH_EXP})
    context = {
        "filterform":filter_form,
        "breadcrumbs":{
            "Data Viewer":"dataviz:vizmain",
            "Community Demographics":"dataviz:demographics",
            "Map Views":"dataviz:demographics_mapviews",
            }
        }
    return render(request, "dataviz/mapviews.html", context)

def data_viz_demographics_charts(request): 
    filter_form = DataFilterForm(request.POST or None)
    if request.method == "POST":
        if filter_form.is_valid():
            print("FilterForm valid ",filter_form.cleaned_data)
        else:
            print("FilterForm not valid!")
    # filter_form.filtertree(includes=INCLUDE_ALL) #no-op
    context = {
        "filterform":filter_form,
        "breadcrumbs":{
            "Data Viewer":"dataviz:vizmain",
            "Community Demographics":"dataviz:demographics",
            "Chart Views":"dataviz:demographics_cartviews",
            }
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
    filter_form.filtertree(includes=INCLUDE_ALL_CONTRIBS)
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
    filter_form.filtertree(includes=INCLUDE_ALL_CONTRIBS)
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
    filter_form.filtertree(includes=INCLUDE_ALL_CONTRIBS)
    context = {
        "filterform":filter_form,
        "breadcrumbs":{
            "Data Viewer":"dataviz:vizmain",
            "Priorities Data":"dataviz:prioritiesdata",
            }
        }
    return render(request, "dataviz/prioritiesdata.html", context)
