from django.urls import path

from nexus.views.dataviz import *

app_name = "dataviz"

urlpatterns = [
    path("", data_viz_main, name="vizmain"),
]
