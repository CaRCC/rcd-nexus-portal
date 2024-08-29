from django.urls import path

from nexus.views.dataviz import *

app_name = "dataviz"

urlpatterns = [
    path("", data_viz_main, name="vizmain"),
    path("demographics", data_viz_demographics, name="demographics"),
    path("demographics/mapviews", data_viz_demographics_maps, name="demographics_mapviews"),
    path("demographics/chartviews", data_viz_demographics_charts, name="demographics_chartviews"),
    path("demographics/scatterplots", data_viz_demographics_scatter, name="demographics_scatterplots"),
    path("capsmodeldata", data_viz_capsmodeldata, name="capsmodeldata"),
    path("prioritiesdata", data_viz_prioritiessdata, name="prioritiesdata"),
]
