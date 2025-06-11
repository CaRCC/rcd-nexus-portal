from django.urls import reverse
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse
from django.http import HttpRequest
from django.shortcuts import redirect, render
from django.utils.safestring import mark_safe
from django.core.exceptions import PermissionDenied, ValidationError
from nexus.utils import demogcharts, cmgraphs
from nexus.models.rcd_profiles import RCDProfile
from nexus.models import CapabilitiesAssessment, CapabilitiesTopic, CapabilitiesQuestion, Institution
import importlib.metadata
from operator import attrgetter
import csv
 
def reports_home(request):
    context = {}
    return render(request, "reports/list.html", context)


def report_new_assessments(request):
    if not request.user.is_staff:
        raise PermissionDenied

    assessments = CapabilitiesAssessment.objects.all().exclude(profile__archived=True).exclude(profile__institution__id__in=Institution.getDemoIDList()).order_by('-profile__year','-pk')[:30]

    for assessment in assessments:
        assessment.members = assessment.profile.memberships.all()
        assessment.simpleCC = cmgraphs.cc_mapping[assessment.profile.institution.carnegie_classification]

    context = {
        "assessments":assessments,
        "count":30,
    }

    return render(request, "reports/new_assessments.html", context)

def report_new_assessments_csv(request):
    if not request.user.is_staff:
        raise PermissionDenied
    
    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(
        content_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="new_profiles.csv"'},
    )

    writer = csv.writer(response)
    writer.writerow(["Profile", "Class", "State", "%Done", "Contributors"])

    assessments = CapabilitiesAssessment.objects.all().exclude(profile__archived=True).exclude(profile__institution__id__in=Institution.getDemoIDList()).order_by('-profile__year','-pk')[:30]

    for assessment in assessments:
        members = None
        for member in assessment.profile.memberships.all():
            if not members:
                members = f'{member.user} ({member.role})'
            else:
                members = members + f';{member.user} ({member.role})'
        simpleCC = cmgraphs.cc_mapping[assessment.profile.institution.carnegie_classification]

        writer.writerow([assessment.profile, simpleCC, assessment.review_status, assessment.completed_percent, members])

    return response    

    profile.members = profile.memberships.all()

def report_prog_assessments(request):
    if not request.user.is_staff:
        raise PermissionDenied

        # .exclude(profile__institution__id__in=Institution.getDemoIDList())\
    assessments = CapabilitiesAssessment.objects.all().exclude(profile__archived=True)\
        .exclude(review_status=CapabilitiesAssessment.ReviewStatusChoices.APPROVED)

    assmntList = list()
    for assessment in assessments:
        if assessment.completed_percent_val > 0:
            assessment.members = assessment.profile.memberships.all()
            assessment.simpleCC = cmgraphs.cc_mapping[assessment.profile.institution.carnegie_classification]
            assmntList.append(assessment)

    assmntList.sort(key=attrgetter('completed_percent_val'), reverse=True)

    context = {
        "assessments":assmntList,
    }

    return render(request, "reports/prog_assessments.html", context)


def report_stale_assessments(request):

    context = {
    }

    return render(request, "reports/stale_assessments.html", context)

