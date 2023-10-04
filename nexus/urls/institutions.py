from django.urls import path

from nexus.views.institutions import *

app_name = "institutions"

urlpatterns = [
    path("-", institution_request, name="request"),
    path("<int:pk>/", institution_edit, name="edit"),
    path("affiliation-request", affiliation_request, name="affiliation-request"),
    path("affiliation-request/<str:token>", affiliation_request, name="affiliation-request-approve"),
]
