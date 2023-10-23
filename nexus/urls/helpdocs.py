from django.urls import path

from nexus.views.helpdocs import *

app_name = "helpdocs"

urlpatterns = [
    path("", help_docs_home, name="main"),
    path("intro_and_guide", help_intro_and_guide, name="intro_and_guide"),
    path("faq", help_faq, name="faq"),
    path("quickstart", help_quickstart, name="quickstart"),
    path("printable_questions", printable_questions, name="printable_questions"),
]
