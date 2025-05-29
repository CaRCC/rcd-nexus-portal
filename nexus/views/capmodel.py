import logging

import csv
from django.apps import apps
from django.contrib import messages
from django.core.mail import send_mail
from django.http import HttpResponseBadRequest, HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.views.decorators.cache import cache_page
from django.core.exceptions import ValidationError

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
        # print("assessment view with no assessment")
        if(request.GET) :
            dict = request.GET.dict()
            atype = dict.get('atype')
            # print(f"assessment GET with atype [{atype}]")
            if atype==CapabilitiesAssessment.AssessmentTypeChoices.FULL \
                or atype==CapabilitiesAssessment.AssessmentTypeChoices.ESSENTIAL:
                assessment, _ = CapabilitiesAssessment.objects.get_or_create(profile_id=profile_id)
            elif atype==CapabilitiesAssessment.AssessmentTypeChoices.CYOJ:
                copy_from = int(dict.get('copy_from'))
                # print(f"CYOJ with copy_from: [{copy_from}]")
                if copy_from == 0:
                    assessment, _ = CapabilitiesAssessment.objects.get_or_create(profile_id=profile_id)
                else:
                    sourceprofile = access_profile(request, copy_from, "view")
                    if hasattr(sourceprofile, "capabilities_assessment"):
                        profile.capabilities_assessment = apps.get_model(
                            "nexus", "CapabilitiesAssessment"
                        ).objects.copy(sourceprofile.capabilities_assessment, profile=profile)
                        profile.comments = f"{profile.comments}\nAssessment data copied from {sourceprofile}."
                        profile.save()
                        profile.refresh_from_db()
                        assessment = profile.capabilities_assessment
                        assessment.copied_from = sourceprofile.capabilities_assessment
                        # print(f"CYOJ copied assessment from copy_from: [{copy_from}] new assessment is: [{assessment.pk}] state: [{assessment.state}]")
                    else: # Source profile has no assessment - should never happen!
                        logger.error(f"Creating Assessment from Source [{copy_from}]; Profile has no assessment!!")
                        assessment, _ = CapabilitiesAssessment.objects.get_or_create(profile_id=profile_id)
            else: 
                logger.error(f"Got Assessment type: [{atype}]")
                # Default to FULL assessment
                assessment, _ = CapabilitiesAssessment.objects.get_or_create(profile_id=profile_id)
                atype=CapabilitiesAssessment.AssessmentTypeChoices.FULL
            assessment.assessment_type = atype
            assessment.update_time = timezone.now()
            assessment.update_user = request.user
            assessment.save()
        else: # No assessment and no context to create one - redirect to the profile. 
            return redirect("rcdprofile:detail", profile.pk)

        profile.refresh_from_db()

    can_submit = request.user.rcd_profile_memberships.filter(profile=profile, role=roles.SUBMITTER).exists()
    submittable = can_submit and assessment.state == CapabilitiesAssessment.State.COMPLETE and assessment.review_status == CapabilitiesAssessment.ReviewStatusChoices.NOT_SUBMITTED

    if submittable:
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
                    f"Your CaRCC Capabilities Assessment for {profile} has been submitted for final review.",
                )
                send_mail(
                    subject=f"CaRCC Capabilities Assessment Submitted for {profile}",
                    message=f"An assessment for Institution Profile: {profile} was just submitted from Institution: {profile.institution}, by: {request.user}.",
                    from_email=settings.DEFAULT_FROM_EMAIL_USER+'@'+request.get_host(),
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
        facing.has_included = False
        facing.has_nonincluded = False
        facing.has_essential = False
        facing.has_nonessential = False
        facing.is_partial = False
        facing_coverage_sum=0
        topic_sum_count=0
        included_topic_count=0
        # print(f"Working through facing {facing.slug}...")
        facing.questionCount = assessment.answers.filter(question__topic__facing=facing).filter_included(assessment).count()
        for topic, answers in topics.items():
            topic.content = topic.contents.get(language=session_language)
            topic.is_partial = False
            filtered_answers = answers.filter_included(assessment)  # set aside the not applicable and not included ones
            if not filtered_answers.exists():
                answers.coverage_color = None
                answers.coverage_pct = "-"
                topic.is_essential = False
                topic.is_included = False
                facing.has_nonincluded = True
                facing.has_nonessential = True
                # print(f"Topic {topic.slug} has no questions used.")
                if(topic.slug!=CapabilitiesTopic.domain_coverage_slug):
                    facing.is_partial = True    # Any missing topic except domain means a partial facing
            else: # There are some questions that are applicable, essential, and/or included
                included_topic_count += 1
                if assessment.assessment_type != CapabilitiesAssessment.AssessmentTypeChoices.FULL:
                    # filtered answers may have copied but not included questions for a cloned CYOJ
                    if answers.filter(is_included=True).exists():
                        facing.has_included = True
                        topic.is_included = True
                    else:
                        facing.has_nonincluded = True
                    if assessment.assessment_type == CapabilitiesAssessment.AssessmentTypeChoices.ESSENTIAL:
                        if filtered_answers.filter(question__is_essential=True).exists():
                            facing.has_essential = True
                            topic.is_essential = True
                        else :  # this topic has no essential questions, so the facing has non-essential topics
                            facing.has_nonessential = True

                if filtered_answers.filter_unanswered().exists():
                    answers.coverage_color = None
                    # Do not have domain coverage contribute to facing coverage, even if they included it explicitly
                    if topic.slug!=CapabilitiesTopic.domain_coverage_slug:
                        facing_coverage_sum = None
                    incomplete = filtered_answers.filter_unanswered().count()
                    totalForTopic = filtered_answers.count()
                    if incomplete != totalForTopic:
                        answers.coverage_pct = mark_safe("<span class=\"wip\">(WIP: "+str(totalForTopic-incomplete)
                                                    +" of "+str(totalForTopic)+")</span>")
                    else :
                        answers.coverage_pct = "-"
                    # print(f"Topic {topic.slug} has {incomplete} unanswered questions out of {totalForTopic} used.")
                else: # All included answers for this topic are answered
                    if topic.slug!=CapabilitiesTopic.domain_coverage_slug and filtered_answers.count() != answers.count():
                        # Topic does not include all the questions and is not a domain coverage topic
                        topic.is_partial = True     # Any missing  means a partial topic
                        facing.is_partial = True    # Any partial topic except domain means a partial facing
                    filtered_topic_answers = filtered_answers.filter(not_applicable=False)
                    if not filtered_topic_answers.exists(): # Can happen if all questions are marked N/A
                        answers.coverage_pct = "N/A"
                        answers.coverage_color = None
                    else: 
                        agg = filtered_topic_answers.aggregate_score()
                        coverage = agg["average"]
                        coverage = min(1.0, max(0.0, coverage))
                        if coverage == None:    # Safety check - should not obtain
                            answers.coverage_pct = "-"
                            answers.coverage_color = None
                        else:
                            covstring = format(coverage, ".1%" if coverage<1.0 else ".0%")
                            answers.coverage_pct = mark_safe(f"{covstring}")
                            answers.coverage_color = compute_answer_color(coverage)
                            # Do not have domain coverage contribute to facing coverage, even if they included it explicitly
                            if facing_coverage_sum != None and topic.slug!=CapabilitiesTopic.domain_coverage_slug:
                                facing_coverage_sum += coverage
                                topic_sum_count += 1
                        # print(f"Topic {topic.slug} has no unanswered questions; coverage is {coverage} for questions used.")
        # Close for topic, answers
        if facing_coverage_sum != None and facing_coverage_sum > 0: # we have coverage on all required/included topics
            facingCov = facing_coverage_sum/topic_sum_count
            covstring = format(facingCov, ".1%" if facingCov<1.0 else ".0%")
            facing.coverage_pct = mark_safe(f"{covstring}")
            facing.coverage_color = compute_answer_color(facingCov)
    # Close for facing, topics

    # Aggregate the domain coverage answers across all the facings. 
    # Note that this is orthogonal to the assessment type (it is either there or not)
    # They can choose to include it for an Essential or CYIG assessment, but it is still handled separately like this. 
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
    filtered_answers = assessment.filtered_answers(excludeNotApplicable=False) 
    total_questions = filtered_answers.count()
    completed_questions = total_questions - filtered_answers.filter_unanswered().count()

    top_priorities = assessment.answers.filter(priority__gt=0).order_by("priority")[:10]
    for answer in top_priorities:
        answer.html_display = mark_safe(f"{answer.question.contents.get(language=session_language).text}")

    context = {
        "profile": profile,
        "atype": assessment.assessment_type,
        "cyoj_copied": not assessment.copied_from is None,
        "can_submit": can_submit,
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
            f"Your CaRCC Capabilities Assessment for {profile} is not pending review and cannot be unsubmitted.",
        )
        return redirect("capmodel:assessment", profile_id)

    assessment.review_status = CapabilitiesAssessment.ReviewStatusChoices.NOT_SUBMITTED
    assessment.update_time = timezone.now()
    assessment.update_user = request.user
    assessment.save()
    messages.success(
        request,
        f"Your CaRCC Capabilities Assessment for {profile} has been unsubmitted.",
    )
    send_mail(
        subject=f"RCD Nexus Assessment Un-Submitted for {profile}",
        message=f"An assessment for RCD Profile: {profile} was just unsubmitted (withdrawn) from Institution: {profile.institution}, by: {request.user}.",
        from_email=settings.DEFAULT_FROM_EMAIL_USER+'@'+request.get_host(),
        recipient_list=[settings.CURATOR_EMAIL],
    )

    return redirect("capmodel:assessment", profile_id)

def topic_is_included(assessment, facing, topic):
    # Topic.included == If any subsumed questions are included (equivalent to NOT(all subsumed questions are NOT included).
    answers = assessment.answers.filter(question__topic__facing_id=facing.pk, question__topic_id=topic.pk, is_included=True)
    return True if answers else False
    
def topic_is_essential(assessment, facing, topic):
    #Topic.essential == any subsumed question is essential
    answers = assessment.answers.filter(question__topic__facing_id=facing.pk, question__topic_id=topic.pk, question__is_essential=True)
    return True if answers else False

def topic(request, profile_id, facing, topic):
    profile = access_profile(request, profile_id, "view")
    assessment = profile.capabilities_assessment

    facing = Facing.objects.get(slug=facing)
    topic = facing.capmodel_topics.get(slug=topic)

    answers = assessment.answers.filter(question__topic__facing_id=facing.pk, question__topic_id=topic.pk).annotate_coverage().order_by("question_id")

    session_language = "en"  # TODO get session language
    all_answered = True
    is_essential = False
    has_nonessential = False
    is_included = False
    has_nonincluded = False
    for answer in answers:
        #answer.qid = {answer.question.legacy.qid if hasattr(answer.question, "legacy") else 'Q'}
        if answer.question.is_essential:
            is_essential = True
        else:
            has_nonessential = True
        if answer.is_included:
            is_included = True
        else:
            has_nonincluded = True
        answer.html_display = mark_safe(f"{answer.question.contents.get(language=session_language).text}")
        answer.coverage_color = None
        # Need to ignore questions not included in this assessment
        if assessment.assessment_type == CapabilitiesAssessment.AssessmentTypeChoices.ESSENTIAL and \
            answer.question.is_essential == False and answer.is_included == False:
                answer.coverage_percent = "-"
        elif assessment.assessment_type == CapabilitiesAssessment.AssessmentTypeChoices.CYOJ and \
            assessment.copied_from == None and answer.is_included == False:
                answer.coverage_percent = "-"
        else:
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
                    all_answered = False
                case CapabilitiesAnswer.State.UNANSWERED:
                    answer.coverage_percent = "-"
                    all_answered = False
                case CapabilitiesAnswer.State.NOT_APPLICABLE:
                    answer.coverage_percent = "N/A"
                    answer.cssclass = "NA"

    coverage_pct = None
    coverage_color = None
    if all_answered:
        agg = answers.filter(not_applicable=False).filter_included(assessment).aggregate_score()
        coverage = agg["average"]
        if coverage != None:
            coverage = min(1.0, max(0.0, coverage))
            covstring = format(coverage, ".1%" if coverage<1.0 else ".0%")
            coverage_pct = mark_safe(f"{covstring}")
            coverage_color = compute_answer_color(coverage)

    prev_topic_list = CapabilitiesTopic.objects.filter(facing__slug=facing.slug, index__lt=topic.index)
    next_topic_list = CapabilitiesTopic.objects.filter(facing__slug=facing.slug, index__gt=topic.index)

    showExtraTopics = request.COOKIES.get('showEX')=="1"
    # print(f"Topic view, showExtraTopics is: [{showExtraTopics}]")
    if assessment.assessment_type == CapabilitiesAssessment.AssessmentTypeChoices.FULL or showExtraTopics:
        prev_topic = prev_topic_list.last()
        next_topic = next_topic_list.first()
    else:
        prev_topic = None
        next_topic = None
        if prev_topic_list.count() > 0:
            for i in range(prev_topic_list.count()-1,-1,-1):
                ptopic = prev_topic_list[i]
                if assessment.assessment_type == CapabilitiesAssessment.AssessmentTypeChoices.ESSENTIAL and topic_is_essential(assessment, facing, ptopic) \
                    or topic_is_included(assessment, facing, ptopic):
                    prev_topic = ptopic
                    break
        if next_topic_list.count() > 0:
            for ntopic in next_topic_list:
                if assessment.assessment_type == CapabilitiesAssessment.AssessmentTypeChoices.ESSENTIAL and topic_is_essential(assessment, facing, ntopic) \
                    or topic_is_included(assessment, facing, ntopic):
                    next_topic = ntopic
                    break


    return render(
        request,
        "capmodel/topic.html",
        {
            "answers": answers,
            "assessment": assessment,
            "atype": assessment.assessment_type,
            "cyoj_copied": not assessment.copied_from is None,
            "facing": facing.contents.get(language=session_language),
            "topic": topic.contents.get(language=session_language),
            "topic_is_domain": topic.slug==CapabilitiesTopic.domain_coverage_slug,
            "is_included": is_included,
            "has_nonincluded": has_nonincluded,
            "is_essential": is_essential,
            "has_nonessential": has_nonessential,
            "coverage_pct": coverage_pct,
            "coverage_color": coverage_color,
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
            answer.assessment.update_user = request.user
            answer.assessment.save()
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
                        f"Capability {answer.question} left unanswered."
                    )
                case CapabilitiesAnswer.State.NOT_APPLICABLE:
                    messages.info(
                        request,
                        f"Capability {answer.question} marked as not applicable."
                    )
            return redirect("capmodel:topic", profile_id, answer.question.topic.facing.slug, answer.question.topic.slug)
        else:
            messages.error(request, "There was an error processing the form.")

    session_language = "en"  # TODO get session language
    question = answer.question.contents.get(language=session_language)
    question.slug = answer.question.slug
    question.is_essential = answer.question.is_essential

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
    if answer.assessment.assessment_type==CapabilitiesAssessment.AssessmentTypeChoices.CYOJ:
        cyoj = True
        cyoj_copied = not answer.assessment.copied_from is None
    else :
        cyoj = False
        cyoj_copied = False

    context = {
        "profile": profile,
        "essentialAssmnt": answer.assessment.assessment_type==CapabilitiesAssessment.AssessmentTypeChoices.ESSENTIAL ,
        "cyojAssmnt": cyoj,
        "cyojAssmntCopied": cyoj_copied,
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


def includequestion(request, profile_id, question_pk):
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid method.")
    
    profile = access_profile(request, profile_id, "edit")
    assessment=profile.capabilities_assessment
    answer = CapabilitiesAnswer.objects.get(assessment=assessment, question_id=question_pk)
    if answer.is_included:
        raise ValidationError("Attempt to include a question that is already included.")
    answer.is_included = True

    # If a CYOJ with a source from which this was copied, clear the answer
    if assessment.assessment_type == CapabilitiesAssessment.AssessmentTypeChoices.CYOJ \
        and not assessment.copied_from is None:
        answer.clear()

    answer.save()

    return redirect("capmodel:answer", profile_id, question_pk)

def removequestion(request, profile_id, question_pk):
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid method.")

    profile = access_profile(request, profile_id, "edit")
    assessment=profile.capabilities_assessment
    answer = CapabilitiesAnswer.objects.get(assessment=assessment, question_id=question_pk)
    
    if not answer.is_included:
        raise ValidationError("Attempt to remove a question that is already included.")
    answer.is_included = False

    if assessment.assessment_type == CapabilitiesAssessment.AssessmentTypeChoices.CYOJ:
        if not assessment.copied_from is None:
            answer_from_copied = CapabilitiesAnswer.objects.get(assessment=assessment.copied_from, question_id=question_pk)
            answer.copy_from(answer_from_copied)
        else: 
            answer.clear()

    if assessment.assessment_type == CapabilitiesAssessment.AssessmentTypeChoices.ESSENTIAL:
        answer.clear()

    answer.save()

    return redirect("capmodel:answer", profile_id, question_pk)

def includetopic(request, profile_id, facing, topic):
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid method.")
    
    profile = access_profile(request, profile_id, "edit")
    assessment=profile.capabilities_assessment

    facingObj = Facing.objects.get(slug=facing)
    topicObj = facingObj.capmodel_topics.get(slug=topic)

    answers = assessment.answers.filter(question__topic__facing_id=facingObj.pk, question__topic_id=topicObj.pk).order_by("question_id")

    for answer in answers:
        # Ignore current included state  since they might add a topic after adding a question or two
        answer.is_included = True
        # If a CYOJ with a source from which this was copied, clear the answer
        if assessment.assessment_type == CapabilitiesAssessment.AssessmentTypeChoices.CYOJ \
            and not assessment.copied_from is None:
            answer.clear()
        answer.save()

    return redirect("capmodel:topic", profile_id, facing, topic)

def removetopic(request, profile_id, facing, topic):
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid method.")

    profile = access_profile(request, profile_id, "edit")
    assessment=profile.capabilities_assessment

    facingObj = Facing.objects.get(slug=facing)
    topicObj = facingObj.capmodel_topics.get(slug=topic)

    answers = assessment.answers.filter(question__topic__facing_id=facingObj.pk, question__topic_id=topicObj.pk).order_by("question_id")

    for answer in answers:
        # Ignore current included state since they might add a topic after adding a question or two
        answer.is_included = False
        if assessment.assessment_type == CapabilitiesAssessment.AssessmentTypeChoices.CYOJ \
            and not assessment.copied_from is None:
            answer_from_copied = CapabilitiesAnswer.objects.get(assessment=assessment.copied_from, question_id=answer.question.pk)
            answer.copy_from(answer_from_copied)
        else: # No source for CYOJ or Essentials assessment
            answer.clear()
        answer.save()

    return redirect("capmodel:topic", profile_id, facing, topic)


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

def printable_report(request, profile_id):
    profile = access_profile(request, profile_id, "view")
    session_language = "en"  # TODO get session language

    assessment = profile.capabilities_assessment
    categories = assessment.answers.annotate_coverage().group_by_facing_topic()

    nFacings = len(categories.keys())
    for facing, topics in categories.items():
        facing.content = facing.contents.get(language=session_language)
        #nTopicsRequired = len(topics.keys())  
        #nTopicsComplete = 0
        #aggSum = 0
        facing.has_included = False
        facing.has_nonincluded = False
        facing.has_essential = False
        facing.has_nonessential = False
        facing.is_partial = False
        facing_coverage_sum=0
        topic_sum_count=0
        included_topic_count=0
        facing.questionCount = assessment.answers.filter(question__topic__facing=facing).filter_included(assessment).count()
        for topic, answers in topics.items():
            topic.content = topic.contents.get(language=session_language)
            topic.is_partial = False
            topic.is_essential = False
            topic.is_included = False
            topic.has_nonessential = False
            topic.has_nonincluded = False
            filtered_answers = answers.filter_included(assessment)  # set aside the not applicable and not included ones
            if not filtered_answers.exists():
                topic.coverage_color = None
                topic.coverage_pct = "-"
                topic.has_nonessential = True
                topic.has_nonincluded = True
                facing.has_nonincluded = True
                facing.has_nonessential = True
                # print(f"Topic {topic.slug} has no questions used.")
                if(topic.slug!=CapabilitiesTopic.domain_coverage_slug):
                    facing.is_partial = True    # Any missing topic except domain means a partial facing
            else: # There are some questions that are applicable, essential, and/or included
                included_topic_count += 1
                if assessment.assessment_type != CapabilitiesAssessment.AssessmentTypeChoices.FULL:
                    # filtered answers may have copied but not included questions for a cloned CYOJ
                    if assessment.assessment_type == CapabilitiesAssessment.AssessmentTypeChoices.ESSENTIAL:
                        if filtered_answers.filter(question__is_essential=True).exists():
                            facing.has_essential = True
                            topic.is_essential = True
                            non_essential_answers = answers.filter(question__is_essential=False)
                            if non_essential_answers.exists():
                                if non_essential_answers.filter(is_included=False).exists():
                                    topic.has_nonessential = True
                                    topic.has_nonincluded = True
                                else:
                                    topic.is_included = True
                        else :  # this topic has no essential questions, but has some included ones (or filtered_answers would be null)
                            facing.has_nonessential = True
                            if answers.filter(is_included=False).exists():
                                topic.has_nonessential = True   # If all Qs non-essential AND included, don't mark as has non-essential
                                topic.has_nonincluded = True
                            topic.is_included = True
                            facing.has_included = True
                    else: # CYOJ
                        if answers.filter(is_included=True).exists():
                            facing.has_included = True
                            topic.is_included = True
                            if answers.filter(is_included=False).exists():
                                topic.has_nonincluded = True
                        else:
                            facing.has_nonincluded = True
                            topic.has_nonincluded = True

                if filtered_answers.filter_unanswered().exists():
                    topic.coverage_color = None
                    # Do not have domain coverage contribute to facing coverage, even if they included it explicitly
                    if topic.slug!=CapabilitiesTopic.domain_coverage_slug:
                        facing_coverage_sum = None
                    incomplete = filtered_answers.filter_unanswered().count()
                    totalForTopic = filtered_answers.count()
                    if incomplete != totalForTopic:
                        topic.coverage_pct = mark_safe("<span class=\"wip\">(WIP: "+str(totalForTopic-incomplete)
                                                    +" of "+str(totalForTopic)+")</span>")
                    else :
                        topic.coverage_pct = "-"
                    # print(f"Topic {topic.slug} has {incomplete} unanswered questions out of {totalForTopic} used.")
                else: # All included answers for this topic are answered
                    if topic.slug!=CapabilitiesTopic.domain_coverage_slug and filtered_answers.count() != answers.count():
                        # Topic does not include all the questions and is not a domain coverage topic
                        topic.is_partial = True     # Any missing  means a partial topic
                        facing.is_partial = True    # Any partial topic except domain means a partial facing

                    filtered_topic_answers = filtered_answers.filter(not_applicable=False)
                    if not filtered_topic_answers.exists(): # Can happen if all questions are marked N/A
                        topic.coverage_pct = "N/A"
                        topic.coverage_color = None
                    else: 
                        agg = filtered_topic_answers.aggregate_score()
                        coverage = agg["average"]
                        coverage = min(1.0, max(0.0, coverage))
                        if coverage == None:    # Safety check - should not obtain
                            topic.coverage_pct = "-"
                            topic.coverage_color = None
                        else:
                            covstring = format(coverage, ".1%" if coverage<1.0 else ".0%")
                            topic.coverage_pct = mark_safe(f"{covstring}")
                            topic.coverage_color = compute_answer_color(coverage)
                            # Do not have domain coverage contribute to facing coverage, even if they included it explicitly
                            if facing_coverage_sum != None and topic.slug!=CapabilitiesTopic.domain_coverage_slug:
                                facing_coverage_sum += coverage
                                topic_sum_count += 1
            #answers = answers.order_by("question_id")
            for answer in answers:
                answer.html_display = mark_safe(f"{answer.question.contents.get(language=session_language).text}")
                match answer.score_deployment:
                    case CapabilitiesAnswer.ScoreDeploymentChoices.NONE:
                        answer.avail = "None"
                    case CapabilitiesAnswer.ScoreDeploymentChoices.TRACKING:
                        answer.avail = "Tracking"
                    case CapabilitiesAnswer.ScoreDeploymentChoices.DEVELOPING:
                        answer.avail = "Planning"
                    case CapabilitiesAnswer.ScoreDeploymentChoices.DEPLOYING:
                        answer.avail = "Parts"
                    case CapabilitiesAnswer.ScoreDeploymentChoices.COMPLETE:
                        answer.avail = "All"
                    case _ :
                        answer.avail = ""

                match answer.score_supportlevel:
                    case CapabilitiesAnswer.ScoreSupportLevelChoices.NONE:
                        answer.sol = "None"
                    case CapabilitiesAnswer.ScoreSupportLevelChoices.UNRELIABLE:
                        answer.sol = mark_safe(f"At&nbsp;Risk")
                    case CapabilitiesAnswer.ScoreSupportLevelChoices.LIGHTS_ON:
                        answer.sol = "Minimal"
                    case CapabilitiesAnswer.ScoreSupportLevelChoices.BASIC:
                        answer.sol = "Basic"
                    case CapabilitiesAnswer.ScoreSupportLevelChoices.PREMIUM:
                        answer.sol = "Strong"
                    case _ :
                        answer.sol = ""

                match answer.score_collaboration:
                    case CapabilitiesAnswer.ScoreCollaborationChoices.NONE:
                        answer.comm = "None"
                    case CapabilitiesAnswer.ScoreCollaborationChoices.TRACKING:
                        answer.comm = "Exploring"
                    case CapabilitiesAnswer.ScoreCollaborationChoices.DEVELOPING:
                        answer.comm = "Engaging"
                    case CapabilitiesAnswer.ScoreCollaborationChoices.SUSTAINING:
                        answer.comm = "Supporting"
                    case CapabilitiesAnswer.ScoreCollaborationChoices.LEADING:
                        answer.comm = "Leading"
                    case _ :
                        answer.comm = ""

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
                        all_answered = False
                    case CapabilitiesAnswer.State.UNANSWERED:
                        answer.coverage_percent = "-"
                        all_answered = False
                    case CapabilitiesAnswer.State.NOT_APPLICABLE:
                        answer.coverage_percent = "N/A"
                        answer.cssclass = "NA"
                # print(f'Q: {answer}: {answer.html_display} {answer.coverage_percent}')

        # Close for topic, answers
        if facing_coverage_sum != None and facing_coverage_sum > 0: # we have coverage on all required/included topics
            facingCov = facing_coverage_sum/topic_sum_count
            covstring = format(facingCov, ".1%" if facingCov<1.0 else ".0%")
            facing.coverage_pct = mark_safe(f"{covstring}")
            facing.coverage_color = compute_answer_color(facingCov)
    # Close for facing, topics

    context = {
        "profile": profile,
        "atype": assessment.assessment_type,
        "cyoj_copied": not assessment.copied_from is None,
        "categories": categories,
        "navtree": rcdprofile_navtree(profile, rcdprofile_navtree.CAPABILITIES),
    }

    return render(request, "capmodel/printable_report.html", context)

def csv_report(request, profile_id):
    profile = access_profile(request, profile_id, "view")

    filename = f"{profile.institution} ({profile.year}).csv"
    response = HttpResponse(
        content_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename='+filename},
    )
    writer = csv.writer(response)
    writer.writerow(["Facing", "Topic", "Capability", "Avail", "SOL", "Comm", "Cov", "Prio"])

    session_language = "en"  # TODO get session language

    assessment = profile.capabilities_assessment
    categories = assessment.answers.annotate_coverage().group_by_facing_topic()

    for facing, topics in categories.items():
        for topic, answers in topics.items():           
            for answer in answers:
                match answer.state:
                    case CapabilitiesAnswer.State.ANSWERED:
                        # Max at 100% since the collaboration boost/discount can push coverage over 1.0 and under 0
                        covvalue = min(1.0, max(0.0, answer.coverage))
                    case CapabilitiesAnswer.State.NOT_APPLICABLE:
                        covvalue = -1
                    case _ :
                        covvalue = ""
                writer.writerow([facing, topic, answer.question.contents.get(language=session_language).text,
                             answer.score_deployment, answer.score_supportlevel, answer.score_collaboration, covvalue, answer.priority ])

    return response

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
