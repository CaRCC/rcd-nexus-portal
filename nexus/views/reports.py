import datetime
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
from nexus.views.rcd_profiles import view_roles, edit_roles, roles, manage_roles, submit_roles
from nexus.models import CapabilitiesAssessment, CapabilitiesTopic, CapabilitiesQuestion, Institution, User
import importlib.metadata
from operator import attrgetter
import csv
 
def reports_home(request):
    context = {}
    return render(request, "reports/list.html", context)


def report_new_assessments(request):
    if not request.user.is_staff:
        raise PermissionDenied

    #.exclude(profile__institution__id__in=Institution.getDemoIDList())
    assessments = CapabilitiesAssessment.objects.all().exclude(profile__archived=True).order_by('-profile__year','-pk')[:30]

    for assessment in assessments:
        assessment.members = assessment.profile.memberships.all()
        assessment.simpleCC = cmgraphs.cc_mapping.get(assessment.profile.institution.carnegie_classification)
        if assessment.simpleCC == None:
            assessment.simpleCC = "Unknown"

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
    writer.writerow(["Profile", "URL", "Inst. Class", "State", "%Done", "Contributors"])

    # .exclude(profile__institution__id__in=Institution.getDemoIDList())
    assessments = CapabilitiesAssessment.objects.all().exclude(profile__archived=True).order_by('-profile__year','-pk')[:30]

    for assessment in assessments:
        members = None
        for member in assessment.profile.memberships.all():
            if not members:
                members = f'{member.user} ({member.role})'
            else:
                members = members + f';{member.user} ({member.role})'
        simpleCC = cmgraphs.cc_mapping[assessment.profile.institution.carnegie_classification]
        simpleCC = cmgraphs.cc_mapping.get(assessment.profile.institution.carnegie_classification)
        if simpleCC == None:
            simpleCC = "Unknown"
        linkToAssmnt = request.build_absolute_uri(reverse("capmodel:assessment", args=[assessment.profile.pk]))

        writer.writerow([assessment.profile, linkToAssmnt, simpleCC, assessment.review_status, assessment.completed_percent, members])

    return response    

    profile.members = profile.memberships.all()

def report_prog_assessments(request):
    if not request.user.is_staff:
        raise PermissionDenied

    in_prog_years = [settings.RCD_DEFAULT_YEAR, settings.RCD_DEFAULT_YEAR-1]
        # .exclude(profile__institution__id__in=Institution.getDemoIDList())\
    assessments = CapabilitiesAssessment.objects.all().exclude(profile__archived=True)\
        .exclude(review_status=CapabilitiesAssessment.ReviewStatusChoices.APPROVED)\
        .filter(profile__year__in=in_prog_years)

    assmntList = list()
    for assessment in assessments:
        if assessment.completed_percent_val > 0:
            assessment.members = assessment.profile.memberships.all()
            assessment.simpleCC = cmgraphs.cc_mapping.get(assessment.profile.institution.carnegie_classification)
            if assessment.simpleCC == None:
                assessment.simpleCC = "Unknown"
            assmntList.append(assessment)

    assmntList.sort(key=attrgetter('completed_percent_val'), reverse=True)

    context = {
        "assessments":assmntList,
        "title":"In Progress Assessments",
        "desc":"Assessments from this year and last that are in progress (not approved, not archived) with at least one assessed capability.",
    }

    return render(request, "reports/prog_assessments.html", context)


def report_stale_assessments(request):
    if not request.user.is_staff:
        raise PermissionDenied

    stale_cut_off = datetime.date.today() - datetime.timedelta(days=365)

        # .exclude(profile__institution__id__in=Institution.getDemoIDList())\
    assessments = CapabilitiesAssessment.objects.all().exclude(profile__archived=True)\
        .exclude(review_status=CapabilitiesAssessment.ReviewStatusChoices.APPROVED)\
        .filter(update_time__lt=stale_cut_off)

    assmntList = list()
    for assessment in assessments:
        if assessment.completed_percent_val > 0:
            assessment.members = assessment.profile.memberships.all()
            assessment.simpleCC = cmgraphs.cc_mapping.get(assessment.profile.institution.carnegie_classification)
            if assessment.simpleCC == None:
                assessment.simpleCC = "Unknown"
            assmntList.append(assessment)

    assmntList.sort(key=attrgetter('completed_percent_val'), reverse=True)

    context = {
        "assessments":assmntList,
        "title":"Stale Assessments",
        "desc":"Assessments in progress (not approved, not archived), last updated more than a year ago with at least one assessed capability.",
    }
    return render(request, "reports/prog_assessments.html", context)

def report_institutions(request):
    if not request.user.is_staff:
        raise PermissionDenied
    
    primary = None
    if(request.GET) :
        dict = request.GET.dict()
        sortcol = dict.get('sort')
        if sortcol in {'name','internet_domain'}:
            primary = sortcol

    if primary:
        institutions = Institution.objects.all().exclude(profiles__isnull=True).order_by(primary)
    else:
        institutions = Institution.objects.all().exclude(profiles__isnull=True).order_by('country', 'state_or_province', 'name')


    context = {
        "count": institutions.count(),
        "institutions":institutions,
    }

    return render(request, "reports/institutions.html", context)

def report_users(request):
    if not request.user.is_staff:
        raise PermissionDenied
    
    users = User.objects.all().exclude(is_staff=True).order_by('last_name')

    userList = list()
    for user in users:
        user.profile_list = RCDProfile.objects.filter_can_view(user)
        for profile in user.profile_list:
            if profile.memberships.filter(user=user, role__in=submit_roles).exists():
                profile.role = "Submitter"
            elif profile.memberships.filter(user=user, role__in=manage_roles).exists():
                profile.role = "Manager"
            elif profile.memberships.filter(user=user, role__in=edit_roles).exists():
                profile.role = "Editor"
            else:
                profile.role = "Viewer"
        userList.append(user)

    # userList.sort(key=attrgetter(key=attrgetter('last_name'))) 

    context = {
        "count": len(userList),
        "users":userList,
    }

    return render(request, "reports/users.html", context)
