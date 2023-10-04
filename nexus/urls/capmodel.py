from django.urls import path

from nexus.views.capmodel import *

app_name = "capmodel"

urlpatterns = [
    path("api/data", aggregate_score),
    path("explore", explore, name="explore"),
    path("<int:profile_id>/", assessment, name="assessment"),
    path("<int:profile_id>/priorities", priorities, name="priorities"),
    path(
        "<int:profile_id>/benchmark",
        legacy_benchmark_report,
        name="assessment-benchmark",
    ),
    # path("<int:profile_id>/submit", views.assessment_submit, name="assessment-submit"),
    path("<int:profile_id>/unsubmit", assessment_unsubmit, name="assessment-unsubmit"),
    path("<int:profile_id>/questions/<slug:facing>/<slug:topic>", topic, name="topic"),
    path("<int:profile_id>/<int:question_pk>", answer, name="answer"),
]
