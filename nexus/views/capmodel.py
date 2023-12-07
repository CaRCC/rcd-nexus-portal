import logging

from django.contrib import messages
from django.core.mail import send_mail
from django.http import HttpResponseBadRequest, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.views.decorators.cache import cache_page

from nexus.forms.capmodel import *
from nexus.models.capmodel import *
from nexus.utils.capmodel import *
from nexus.views.rcd_profiles import access_profile, view_roles, edit_roles, roles, manage_roles
from nexus.views.rcd_profiles import navtree as rcdprofile_navtree
from nexus.utils.navtree import NavNode
#from nexus.facing import Facing
from nexus.models.facings import Facing

logger = logging.getLogger(__name__)

class aggDomainInfo():
    def __init__(self, coverage_pct, coverage_color):
        self.pct = coverage_pct
        self.color = coverage_color


def assessment(request, profile_id):
    profile = access_profile(request, profile_id, "view")

    try:
        assessment = profile.capabilities_assessment
    except CapabilitiesAssessment.DoesNotExist:
        assessment, _ = CapabilitiesAssessment.objects.get_or_create(
            profile_id=profile_id
        )
        profile.refresh_from_db()

    can_submit = request.user.rcd_profile_memberships.filter(profile=profile, role=roles.SUBMITTER).exists() and assessment.state == CapabilitiesAssessment.State.COMPLETE and assessment.review_status == CapabilitiesAssessment.ReviewStatusChoices.NOT_SUBMITTED

    if can_submit:
        submit_form = CapabilitiesAssessmentSubmitForm(request.POST or None)
        if request.method == "POST":
            if (
                submit_form.is_valid
                and assessment.review_status
                == CapabilitiesAssessment.ReviewStatusChoices.NOT_SUBMITTED
            ):
                assessment.review_status = CapabilitiesAssessment.ReviewStatusChoices.PENDING
                assessment.update_time = timezone.now()
                assessment.update_user = request.user
                assessment.save()
                messages.success(
                    request,
                    f"Your RCD Capabilities Assessment for {profile} has been submitted for final review.",
                )
                send_mail(
                    subject=f"RCD Nexus Assessment Submitted for {profile}",
                    message=f"An assessment for RCD Profile: {profile} was just submitted from Institution: {profile.institution}, by: {request.user}.",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.CURATOR_EMAIL],
                )
                return redirect("capmodel:assessment", profile_id)
    else:
        submit_form = None

    categories = assessment.answers.group_by_facing_topic()

    session_language = "en"  # TODO get session language

    nFacings = len(categories.keys())
    for facing, topics in categories.items():
        facing.content = facing.contents.get(language=session_language)
        # Ignore the domain coverage topic in each facing
        nTopicsRequired = len(topics.keys())-1  
        nTopicsComplete = 0
        aggSum = 0
        for topic, answers in topics.items():
            topic.content = topic.contents.get(language=session_language)
            if answers.filter_unanswered().exists():
                answers.coverage_color = None
                incomplete = answers.filter_unanswered().count()
                totalForTopic = answers.count()
                if incomplete != totalForTopic:
                    answers.coverage_pct = mark_safe("<span class=\"wip\">(WIP: "+str(totalForTopic-incomplete)
                                                +" of "+str(totalForTopic)+")</span>")
                else :
                    answers.coverage_pct = "-"
            else:
                agg = answers.aggregate_score()
                coverage = agg["average"]
                if coverage != None:
                    covstring = format(coverage, ".1%" if coverage<1.0 else ".0%")
                    answers.coverage_pct = mark_safe(f"{covstring}")
                    answers.coverage_color = compute_answer_color(coverage)
                    # Do not include domain coverage in the aggregated Facing coverage
                    if(topic.slug!=CapabilitiesTopic.domain_coverage_slug) :
                        nTopicsComplete += 1
                        aggSum += coverage
                else:
                    answers.coverage_pct = "-"
                    answers.coverage_color = None
        if nTopicsComplete == nTopicsRequired:
            facingCov = aggSum/nTopicsRequired
            covstring = format(facingCov, ".1%" if facingCov<1.0 else ".0%")
            facing.coverage_pct = mark_safe(f"{covstring}")
            facing.coverage_color = compute_answer_color(facingCov)
#        elif nTopicsComplete == 0:
#            facing.coverage_pct = "-"
#        else:
#            facing.coverage_pct = mark_safe("<span class=\"wip\">WIP: "+str(nTopicsComplete)
#                                                +" of "+str(nTopics)+"</span>")
            

    domains = {}
    for d in CapabilitiesQuestion.domain_lookup.keys():
        domaincovs = assessment.answers.filter(question__slug=d, not_applicable=False)
        ndomaincovs = domaincovs.count() - domaincovs.filter_unanswered().count()
        nadomains = assessment.answers.filter(question__slug=d, not_applicable=True).count()
        coverage_color = None                   # default
        if nadomains == nFacings:               # All Facings marked the domain N/A
            coverage_pct = "N/A"
        elif ndomaincovs == 0:                  # None of the applicable domains are answered
            coverage_pct = "-"
        elif ndomaincovs != nFacings-nadomains: # Some applicable domains are unanswered
            coverage_pct = mark_safe("<span class=\"wip\">(WIP: "+str(ndomaincovs+nadomains)
                                                +" of "+str(nFacings)+")</span>")
        else:                                   # All applicable domains are answered
            agg = domaincovs.aggregate_score()
            avgCoverage = agg["average"]
            if avgCoverage == None:
                logger.error("Got unexpected None as average of Domains for Profile: "+ str(profile_id))
                coverage_pct = "-"
            else:
                covstring = format(avgCoverage, ".1%" if avgCoverage<1.0 else ".0%")
                coverage_pct = mark_safe(f"{covstring}")
                coverage_color = compute_answer_color(avgCoverage)
        domains[CapabilitiesQuestion.domain_lookup[d]] = aggDomainInfo(coverage_pct,coverage_color)

    # Filter the domain coverage questions when calculating progress 
    filtered_answers = assessment.answers.exclude(question__slug__in=CapabilitiesQuestion.domain_lookup.keys()) 
    total_questions = filtered_answers.count()
    completed_questions = total_questions - filtered_answers.filter_unanswered().count()

    top_priorities = assessment.answers.filter(priority__gt=0).order_by("priority")[:10]
    for answer in top_priorities:
        answer.html_display = mark_safe(f"{answer.question.contents.get(language=session_language).text}")

    context = {
        "profile": profile,
        "submit_form": submit_form,
#        "facing_coverages": facing_coverages,
        "categories": categories,
        "domains": domains,
        "completed_questions": completed_questions,
        "modified_questions": assessment.answers.filter(is_modified=True).count(),
        "top_priorities": top_priorities,
        "total_questions": total_questions,
        "pct_complete": completed_questions/total_questions if total_questions else 0,
        "navtree": rcdprofile_navtree(profile, rcdprofile_navtree.CAPABILITIES),
    }

    return render(request, "capmodel/assessment.html", context)

def assessment_unsubmit(request, profile_id):
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid method.")

    profile = access_profile(request, profile_id, "submit")

    assessment = profile.capabilities_assessment

    if assessment.review_status != CapabilitiesAssessment.ReviewStatusChoices.PENDING:
        messages.error(
            request,
            f"Your RCD Capabilities Assessment for {profile} is not pending review and cannot be unsubmitted.",
        )
        return redirect("capmodel:assessment", profile_id)

    assessment.review_status = CapabilitiesAssessment.ReviewStatusChoices.NOT_SUBMITTED
    assessment.update_time = timezone.now()
    assessment.update_user = request.user
    assessment.save()
    messages.success(
        request,
        f"Your RCD Capabilities Assessment for {profile} has been unsubmitted.",
    )
    send_mail(
        subject=f"RCD Nexus Assessment Un-Submitted for {profile}",
        message=f"An assessment for RCD Profile: {profile} was just unsubmitted (withdrawn) from Institution: {profile.institution}, by: {request.user}.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.CURATOR_EMAIL],
    )

    return redirect("capmodel:assessment", profile_id)


def topic(request, profile_id, facing, topic):
    profile = access_profile(request, profile_id, "view")
    assessment = profile.capabilities_assessment

    facing = Facing.objects.get(slug=facing)
    topic = facing.capmodel_topics.get(slug=topic)

    answers = assessment.answers.filter(question__topic__facing_id=facing.pk, question__topic_id=topic.pk).annotate_coverage().order_by("question_id")

    session_language = "en"  # TODO get session language
    for answer in answers:
        #answer.qid = {answer.question.legacy.qid if hasattr(answer.question, "legacy") else 'Q'}
        answer.html_display = mark_safe(f"{answer.question.contents.get(language=session_language).text}")
        answer.coverage_color = None
        match answer.state:
            case CapabilitiesAnswer.State.ANSWERED:
                # Max at 100% since the collaboration boost/discount can push coverage over 1.0 and under 0
                covvalue = min(1.0, max(0.0, answer.coverage))
                covstring = format(covvalue, ".1%" if covvalue<1.0 else ".0%")
                answer.coverage_percent = mark_safe(f"{covstring}")        
                answer.coverage_color = compute_answer_color(answer.coverage)
            case CapabilitiesAnswer.State.PARTIALLY_ANSWERED:
                answer.coverage_percent = "(WIP)"
                answer.cssclass = "WIP"
            case CapabilitiesAnswer.State.UNANSWERED:
                answer.coverage_percent = "-"
            case CapabilitiesAnswer.State.NOT_APPLICABLE:
                answer.coverage_percent = "N/A"
                answer.cssclass = "NA"


    prev_topic = CapabilitiesTopic.objects.filter(
        facing__slug=facing.slug, index__lt=topic.index
    ).last()

    next_topic = CapabilitiesTopic.objects.filter(
        facing__slug=facing.slug, index__gt=topic.index
    ).first()



    return render(
        request,
        "capmodel/topic.html",
        {
            "answers": answers,
            "assessment": assessment,
            "facing": facing.contents.get(language=session_language),
            "topic": topic.contents.get(language=session_language),
            "prev_topic": prev_topic,
            "next_topic": next_topic,
            "navtree": rcdprofile_navtree(profile, rcdprofile_navtree.CAPABILITIES),
        },
    )



def answer(request, profile_id, question_pk):
#def answer(request, profile_id, facing_slug, topic_slug, question_slug):
    profile = access_profile(request, profile_id, "view")
    answer = CapabilitiesAnswer.objects.annotate_coverage().get(
        assessment=profile.capabilities_assessment, question_id=question_pk
        #assessment=profile.capabilities_assessment, question__slug=question_slug, question__topic__slug=topic_slug, question__topic__facing__slug=facing_slug
    )

    form = CapabilitiesAnswerForm(request.POST or None, instance=answer)
    if request.method == "POST":
        if answer.assessment.is_frozen:
            messages.error(
                request,
                "This assessment has been submitted and included in community datasets and can no longer be modified.",
            )
        elif form.is_valid():
            answer: CapabilitiesAnswer = form.save(commit=False)
            answer.is_modified = True
            answer.save()
            match answer.state:
                case CapabilitiesAnswer.State.ANSWERED:
                    messages.success(request, f"Answer updated for {answer.question}.")
                case CapabilitiesAnswer.State.PARTIALLY_ANSWERED:
                    messages.warning(
                        request,
                        f"Partial answer updated for {answer.question}.",
                    )
                case CapabilitiesAnswer.State.UNANSWERED:
                    messages.info(
                        request,
                        f"Question {answer.question} left unanswered."
                    )
                case CapabilitiesAnswer.State.NOT_APPLICABLE:
                    messages.info(
                        request,
                        f"Question {answer.question} marked as not applicable."
                    )
            return redirect("capmodel:topic", profile_id, answer.question.topic.facing.slug, answer.question.topic.slug)
        else:
            messages.error(request, "There was an error processing the form.")

    session_language = "en"  # TODO get session language
    question = answer.question.contents.get(language=session_language)
    question.slug = answer.question.slug

    match answer.state:
        case CapabilitiesAnswer.State.ANSWERED:
            covvalue = min(1.0, max(0.0, answer.coverage))
            covstring = format(covvalue, ".1%" if covvalue<1.0 else ".0%")
        case CapabilitiesAnswer.State.PARTIALLY_ANSWERED:
            covstring = "Work in Progress (WIP)"
        case CapabilitiesAnswer.State.UNANSWERED:
            covstring = ""
        case CapabilitiesAnswer.State.NOT_APPLICABLE:
            covstring = "N/A"

    other_answers = CapabilitiesAnswer.objects.order_by("question_id").filter(
        assessment__profile_id=profile_id
    )

    context = {
        "profile": profile,
        "answer": answer,
        "question": question,
        "can_edit": request.user.rcd_profile_memberships.filter(
            profile=profile, role__in=edit_roles
        ).exists(),
        "form": form,
        "topic": answer.question.topic.contents.get(language=session_language),
        "facing": answer.question.topic.facing.contents.get(language=session_language),
        "coverage": covstring,
        "prev_question_pk": (
            other_answers.filter(question_id__lt=question_pk).last()
            or other_answers.last()
        ).question_id,
        "next_question_pk": (
            other_answers.filter(question_id__gt=question_pk).first()
            or other_answers.first()
        ).question_id,
        "navtree": rcdprofile_navtree(profile, rcdprofile_navtree.CAPABILITIES),
    }

    return render(request, "capmodel/answer.html", context)


def legacy_benchmark_report(request, profile_id):
    assessment = CapabilitiesAssessment.objects.get(profile_id=profile_id)
    # answers = CapabilitiesAnswer.objects.from_get_request(request)
    answers = CapabilitiesAnswer.objects.all()

    benchmarks = dict()
    benchmarks["R1"] = answers.filter(
        assessment__entity__xattrs__carnegieclassification="R1"
    ).benchmark(
        "question__entity__xattrs__facing",
        "question__entity__xattrs__topic",
        assessment_id=assessment.pk,
    )
    benchmarks["R2"] = answers.filter(
        assessment__entity__xattrs__carnegieclassification="R2"
    ).benchmark(
        "question__entity__xattrs__facing",
        "question__entity__xattrs__topic",
        assessment_id=assessment.pk,
    )
    benchmarks["EPSCOR"] = answers.filter(
        assessment__entity__xattrs__epscor="Yes"
    ).benchmark(
        "question__entity__xattrs__facing",
        "question__entity__xattrs__topic",
        assessment_id=assessment.pk,
    )
    benchmarks["MSI"] = answers.exclude(
        assessment__entity__xattrs__minorityserving="Not a minority serving institution"
    ).benchmark(
        "question__entity__xattrs__facing",
        "question__entity__xattrs__topic",
        assessment_id=assessment.pk,
    )

    return render(
        request, "capmodel/assessment_benchmark.html", {
            "benchmarks": benchmarks}
    )



def priorities(request, profile_id):
    profile = access_profile(request, profile_id, "view")

    assessment = profile.capabilities_assessment

    session_language = "en"  # TODO get session language
    answers = assessment.answers.filter(priority__gt=0).order_by("priority")
    for answer in answers:
        answer.html_display = mark_safe(f"{answer.question.contents.get(language=session_language).text}")

    context = {
        "profile": profile,
        "answers": answers,
        "navtree": rcdprofile_navtree(profile, rcdprofile_navtree.CAPABILITIES),
    }

    return render(request, "capmodel/priorities.html", context)



# delete?
# def api_aggregate_score?
def aggregate_score(request):
    scoring = request.GET.get("scoring", "coverage")
    facets = request.GET.get("facet", [])
    if facets != []:
        facets = facets.split(",")

    answers = CapabilitiesAnswer.objects.from_get_request(request)

    scores = answers.aggregate_score(
        *facets, scoring_method=scoring, min_samples=1)

    return JsonResponse(
        {"data": list(scores)},
    )
# delete
def explore(request):
    return render(request, "capmodel/test-viz.html")
