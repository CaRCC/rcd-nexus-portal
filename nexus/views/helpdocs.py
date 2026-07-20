from datetime import datetime
from django.utils import timezone
from django.urls import reverse
from django.conf import settings
from django.contrib import messages
from django.http import HttpRequest
from django.shortcuts import redirect, render
from django.utils.safestring import mark_safe
from nexus.utils import demogcharts
from nexus.models.rcd_profiles import RCDProfile
from nexus.models import CapabilitiesAssessment, CapabilitiesTopic, CapabilitiesQuestion
import importlib.metadata
 
def help_docs_home(request):
    version = importlib.metadata.version('rcd-nexus-portal')
    context = {
        "version":version,
    }
    return render(request, "helpdocs/main.html", context)

def getNUsers():
    profiles = demogcharts.getAllProfiles()
    institutions = profiles.values_list('institution__name')
    nInsts = institutions.count()
    return nInsts

def getNContribs():
    profiles = demogcharts.getAllProfiles(pop='contrib').filter(institution__list_as_contributor=True)
    institutions = profiles.values_list('institution__name')
    nInsts = institutions.count()
    nAssessments = RCDProfile.objects.filter(capabilities_assessment__review_status=CapabilitiesAssessment.ReviewStatusChoices.APPROVED).count()
    return nInsts, nAssessments

def help_faq(request):
    nInsts, nAssessments = getNContribs()

    context = {
        "nUsers":getNUsers(),
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
    nInsts, nAssessments = getNContribs()

    context = {
        "nUsers":getNUsers(),
        "nInsts":nInsts,
        "nAssessments":nAssessments,
    }

    return render(request, "helpdocs/dv_faq.html", context)

def printable_questions(request):
    session_language = "en"  # TODO get session language

    filterdate=None
    if(request.GET) :
        dict = request.GET.dict()
        version = dict.get('version')
        match version:
            case "2.0":
                filterdate = datetime(2023, 9, 1, tzinfo=timezone.utc)  # Just before 2.1 release
            case "2.1":
                filterdate = datetime(2023, 10, 10, tzinfo=timezone.utc)  # Just after 2.1 release
            case "3.0":
                filterdate = datetime(2026, 9, 1, tzinfo=timezone.utc)  # Somewhere after 2.0 release guess

    categories = CapabilitiesQuestion.objects.filter_valid(filterdate).group_by_facing_topic()
    nFacings = len(categories.keys())
    for facing, topics in categories.items():
        facing.content = facing.contents.get(language=session_language)
        facingAnchorPrefix = None
        match facing.slug:
            case "researcher":
                facingAnchorPrefix = "rf"
            case "data":
                facingAnchorPrefix = "df"
            case "software":
                facingAnchorPrefix = "swf"
            case "systems":
                facingAnchorPrefix = "syf"
            case "strategy":
                facingAnchorPrefix = "spf"
        facing.anchorid = facingAnchorPrefix+"topics"
        for topic, questions in topics.items():
            topic.content = topic.contents.get(language=session_language)
            topic.anchorid = facingAnchorPrefix+topic.slug+"_qs"
            topic.is_essential = False
            if(topic.slug==CapabilitiesTopic.domain_coverage_slug):
                topic.isdomain = True
            for question in questions:
                qtext = question.contents.get(language=session_language)
                if not qtext.help_text:
                    question.html_display = mark_safe(f"{qtext.text}")
                else:
                    question.html_display = mark_safe(f'{qtext.text}<br><span class="question-help">{qtext.help_text}</span>')
                if question.is_essential:
                    topic.is_essential = True

    context = {
        "categories": categories,
    }

    return render(request, "helpdocs/printable_questions.html", context)

