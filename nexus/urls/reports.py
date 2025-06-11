from django.urls import path

from nexus.views.reports import *

app_name = "reports"

urlpatterns = [
    path("", reports_home, name="list"),
    path("new_assessments", report_new_assessments, name="new_assessments"),
    path("new_assessments_csv", report_new_assessments_csv, name="new_assessments_csv"),
    path("prog_assessments", report_prog_assessments, name="prog_assessments"),
    path("stale_assessments", report_stale_assessments, name="stale_assessments"),
]
