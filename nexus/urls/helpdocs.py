from django.urls import path

from nexus.views.helpdocs import *

app_name = "helpdocs"

urlpatterns = [
    path("", help_docs_home, name="main"),
    path("intro_and_guide", help_intro_and_guide, name="intro_and_guide"),
    path("faq", help_faq, name="faq"),
    path("quickstart", help_quickstart, name="quickstart"),
    path("printable_questions", printable_questions, name="printable_questions"),
    path("dv_intro_and_guide", help_dv_intro_and_guide, name="dv_intro_and_guide"),
    path("dv_faq", help_dv_faq, name="dv_faq"),
    path("dv_quickstart", help_dv_quickstart, name="dv_quickstart"),
]
