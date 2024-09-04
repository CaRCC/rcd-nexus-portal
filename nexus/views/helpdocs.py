from django.urls import reverse
from django.conf import settings
from django.contrib import messages
from django.http import HttpRequest
from django.shortcuts import redirect, render
from nexus.utils import demogcharts
from nexus.models.rcd_profiles import RCDProfile
from nexus.models import CapabilitiesAssessment

def help_docs_home(request):
    return render(request, "helpdocs/main.html", {})

def help_faq(request):
    profiles = demogcharts.getAllProfiles(pop='contrib').filter(institution__list_as_contributor=True)
    institutions = profiles.values_list('institution__name')
    nInsts = institutions.count()
    nAssessments = RCDProfile.objects.filter(capabilities_assessment__review_status=CapabilitiesAssessment.ReviewStatusChoices.APPROVED).count()

    context = {
        "nInsts":nInsts,
        "nAssessments":nAssessments,
    }

    return render(request, "helpdocs/faq.html", context)

def help_intro_and_guide(request):
    context = {}

    return render(request, "helpdocs/intro_and_guide.html", context)

def help_quickstart(request):
    context = {}

    return render(request, "helpdocs/quickstart.html", context)

def help_dv_intro_and_guide(request):
    context = {}

    return render(request, "helpdocs/dv_intro.html", context)

def help_dv_quickstart(request):
    context = {}

    return render(request, "helpdocs/dv_quickstart.html", context)

def help_dv_faq(request):
    context = {}

    return render(request, "helpdocs/dv_faq.html", context)

def printable_questions(request):
    context = {}

    return render(request, "helpdocs/printable_questions.html", context)

