from django.urls import path

from nexus.views.viz import *

app_name = "viz"

urlpatterns = [
    path("", index, name="main"),
   
]
