from datetime import datetime

from django.conf import settings
from django.db import models
from django.db.models import Avg, Count, F, StdDev, Window
from django.db.models.functions import  Least, PercentRank
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _

from nexus.models.facings import Facing
from nexus.utils.fields import FloatChoices
from enum import Enum

from .assessments import AssessmentBase

class CapabilitiesTopic(models.Model):
    """
    Facing topic.
    """
    class Manager(models.Manager):
        def get_by_natural_key(self, facing: str, topic: str):
            return self.get(slug=topic, facing__slug=facing)
        
    objects = Manager()

    facing = models.ForeignKey("nexus.Facing", on_delete=models.CASCADE, related_name="capmodel_topics")
    slug = models.CharField(max_length=50)
    index = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Position of this topic in its facing's topics.")

    def natural_key(self):
        return (self.facing.slug, self.slug)

    def __str__(self):
        return f"{self.facing}.{self.slug}"
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['facing', 'slug'], name='unique_topic')
        ]
        ordering = ["facing", "index", "slug"]


class CapabilitiesTopicContent(models.Model):
    """
    Language-specific content for a facing-topic.
    """
    class Manager(models.Manager):
        def get_by_natural_key(self, facing: str, topic: str, language: str):
            return self.get(topic__slug=topic, topic__facing__slug=facing, language=language)
        
    objects = Manager()

    topic = models.ForeignKey(
        CapabilitiesTopic,
        on_delete=models.CASCADE,
        related_name="contents",
    )
    language = models.CharField(
        max_length=8,
        choices=settings.LANGUAGES,
        default="en",
    )
    display_name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    def natural_key(self):
        return (self.topic.facing.slug, self.topic.slug, self.language)

    def __str__(self):
        return f"[{self.language.upper()}] {self.topic}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["topic", "language"], name="%(app_label)s_%(class)s_unique"
            )
        ]

class CapabilitiesQuestion(models.Model):
    class QuerySet(models.QuerySet):
        def get_by_natural_key(self, facing: str, topic: str, question: str):
            return self.get(slug=question, topic__slug=topic, topic__facing__slug=facing)

        def filter_valid(self, at: datetime = None):
            at = at or timezone.now()
            return self.filter(valid_after__lte=at).exclude(valid_before__lt=at)

    objects = QuerySet.as_manager()

    slug = models.SlugField(
        max_length=255,
        help_text="A short and meaningful text identifier for this question.",
    )

    topic = models.ForeignKey(
        CapabilitiesTopic,
        on_delete=models.CASCADE,
        related_name="questions",
    )

    index = models.PositiveSmallIntegerField(
        help_text="The index of this question in its topic.",
    )

    attrs = models.JSONField(
        default=dict,
        help_text="A JSON object containing additional queryable attributes for this question.",
    )

    valid_after = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="This question will only be included in assessments created after this time.",
    )
    valid_before = models.DateTimeField(
        null=True,
        db_index=True,
        help_text="This question will only be included in assessments created before this time.",
    )

    @property
    def legacy_qid(self):
        return self.attrs.get("legacy_qid")
    
    @property
    def fully_qualified_slug(self):
        return ".".join(self.natural_key())

    def natural_key(self):
        return (self.topic.facing.slug, self.topic.slug, self.slug)

    def __str__(self):
        return self.fully_qualified_slug
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['topic', 'slug'], name='unique_question')
        ]


class CapabilitiesQuestionContent(models.Model):
    class Manager(models.Manager):
        def get_by_natural_key(self, facing: str, topic: str, question: str, language: str):
            return self.get(question__slug=question, question__topic__slug=topic, question__topic__facing__slug=facing, language=language,)
        
    objects = Manager()

    question = models.ForeignKey(
        CapabilitiesQuestion,
        on_delete=models.CASCADE,
        related_name="contents",
    )
    language = models.CharField(
        max_length=8,
        choices=settings.LANGUAGES,
        default="en",
    )
    text = models.TextField()
    help_text = models.TextField(
        blank=True,
        null=True,
    )

    def natural_key(self):
        return (self.question.topic.facing.slug, self.question.topic.slug, self.question.slug, self.language)

    def __str__(self):
        return f"[{self.language.upper()}] {self.question}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["question", "language"], name="%(app_label)s_%(class)s_unique"
            )
        ]
        indexes = [models.Index(fields=["question", "language"])]


class CapabilitiesAssessment(AssessmentBase):
    class QuerySet(models.QuerySet):
        def create(self, *args, **kwargs):
            """
            Create an assessment with answer stubs for all currently valid questions.
            """
            assessment = super().create(*args, **kwargs)
            for question in CapabilitiesQuestion.objects.filter_valid():
                assessment.answers.create(question=question)
            return assessment

        def copy(self, existing, **kwargs):
            """
            Create an assessment with the same answers as an existing assessment (only for overlapping questions).

            Note that the new assessment might have an updated question set that is not identical to the existing assessment.
            """
            assessment = self.create(**kwargs)
            for answer in assessment.answers.all():
                ex_answer = existing.answers.filter(
                    question=answer.question).first()
                if not ex_answer:
                    continue
                answer.score_deployment = ex_answer.score_deployment
                answer.score_collaboration = ex_answer.score_collaboration
                answer.score_supportlevel = ex_answer.score_supportlevel
                answer.work_notes = ex_answer.work_notes
                answer.save()

    objects = QuerySet.as_manager()

    profile = models.OneToOneField(
        "nexus.RCDProfile",
        on_delete=models.CASCADE,
        related_name="capabilities_assessment",
    )

    class State(Enum):
        NOT_STARTED = "not_started"
        IN_PROGRESS = "in_progress"
        COMPLETE = "complete"

    @property
    def state(self) -> "CapabilitiesAssessment.State":
        answers = self.answers.filter(not_applicable=False)
        total = answers.count()
        answered = answers.filter(score_deployment__isnull=False, score_collaboration__isnull=False, score_supportlevel__isnull=False).count()

        if answered == 0:
            return CapabilitiesAssessment.State.NOT_STARTED
        elif answered < total:
            return CapabilitiesAssessment.State.IN_PROGRESS
        else:
            return CapabilitiesAssessment.State.COMPLETE



class CapabilitiesAnswer(models.Model):
    class Manager(models.Manager):
        def from_get_request(self, request):
            """
            Return the QuerySet of Answers according to `facet`, `afilter`, and `qfilter` GET params.
            """
            assessment_filters = request.GET.get("afilter")
            question_filters = request.GET.get("qfilter")

            assessments = CapabilitiesAssessment.objects.all()
            if assessment_filters:
                for filter in assessment_filters.split(","):
                    assessments = assessments.filter(**{"attrs__"+k: v for k,v in filter.split(":")})

            questions = CapabilitiesQuestion.objects.all()
            if question_filters:
                for filter in question_filters.split(","):
                    questions = questions.filter(**{"attrs__"+k: v for k,v in filter.split(":")})

            return self.filter(assessment__in=assessments, question__in=questions)

    class QuerySet(models.QuerySet):
        _coverage = {
            # Based on 2021 formula: average the deployment and supportlevel scores, then scale by 90%-100% based on collaboration score
            # This function is smooth unlike the 2021 formula
            # If we want a non-linear scaling on the collaboration factor, we should raise the order of the function instead of making it piecewise
            "2023": ((F("score_deployment") + F("score_supportlevel")) / 2) * (0.9 + 0.2*F("score_collaboration"))

            ## PRE-NORMALIZATION FORMULAE -- DO NOT USE WITHOUT ADJUSTING
            # "2020": 1
            # - (
            #     (5 - F("score_deployment"))
            #     + (5 - F("score_collaboration")) * 0.5
            #     + (5 - F("score_supportlevel"))
            # )
            # / (4 + 4 * 0.5 + 4),
            # "2021": Least(1.0, ((
            #     1
            #     - ((5 - F("score_deployment")) + (5 - F("score_supportlevel")))
            #     / (4 + 4)
            # )
            # * ((0.9) + ((F("score_collaboration") - 1) * 2/3 * 0.1)))),
            ##
        }
        COVERAGE_FORMULA = _coverage["2023"]
        scoring = {
            "coverage": {
                "average": Avg(COVERAGE_FORMULA),
                "stddev": StdDev(COVERAGE_FORMULA),
                "samples": Count("assessment__profile", distinct=True),
            },
            "deployment": {
                "average": Avg(F("score_deployment")),
                "stddev": StdDev(F("score_deployment")),
                "samples": Count("assessment__profile", distinct=True),
            },
            "collaboration": {
                "average": Avg(F("score_collaboration")),
                "stddev": StdDev(F("score_collaboration")),
                "samples": Count("assessment__profile", distinct=True),
            },
            "supportlevel": {
                "average": Avg(F("score_supportlevel")),
                "stddev": StdDev(F("score_supportlevel")),
                "samples": Count("assessment__profile", distinct=True),
            },
        }

        def filter_unanswered(self):
            return self.exclude(not_applicable=True).filter(models.Q(score_deployment__isnull=True) | models.Q(score_collaboration__isnull=True) | models.Q(score_supportlevel__isnull=True))

        def annotate_coverage(self):
            return self.annotate(coverage=CapabilitiesAnswer.QuerySet.COVERAGE_FORMULA)

        def aggregate_score(self, *facets, scoring_method="coverage", min_samples=1):
            if facets:
                return (
                    self.values(*facets)
                    .annotate(**CapabilitiesAnswer.QuerySet.scoring[scoring_method])
                    .filter(samples__gte=min_samples)
                )
            else:  # Aggregate everything
                result = self.aggregate(
                    **CapabilitiesAnswer.QuerySet.scoring[scoring_method]
                )
                if result["samples"] < min_samples:
                    for key in result:
                        if key != "samples":
                            result[key] = None
                return result

        def benchmark(self, *facets, assessment_id=None):
            if (
                assessment_id != None
                and not self.filter(assessment_id=assessment_id).exists()
            ):
                self = self | CapabilitiesAnswer.objects.filter(
                    assessment_id=assessment_id
                )

            if facets:
                scores = self.aggregate_score("assessment_id", *facets).annotate(
                    percentile=Window(
                        expression=PercentRank(),
                        partition_by=[F(f) for f in facets],
                        order_by=F("average").asc(),
                    )
                )
            else:
                scores = self.aggregate_score("assessment_id").annotate(
                    percentile=Window(
                        expression=PercentRank(), order_by=F("average").asc()
                    )
                )

            if assessment_id != None:
                return [s for s in scores if s["assessment_id"] == assessment_id]

            return scores

        def group_by_facing_topic(self):
            results = dict()
            # TODO can filter by facing and topic with arguments

            for facing in Facing.objects.all():
                results[facing] = dict()
                for topic in facing.capmodel_topics.all():
                    answers = self.filter(question__topic=topic)
                    if answers:
                        results[facing][topic] = answers

            return results

    objects = Manager.from_queryset(QuerySet)()

    assessment = models.ForeignKey(
        CapabilitiesAssessment,
        on_delete=models.CASCADE,
        related_name="answers",
    )
    question = models.ForeignKey(
        CapabilitiesQuestion,
        on_delete=models.RESTRICT,
        related_name="answers",
    )

    class ScoreDeploymentChoices(FloatChoices):
        NONE = 0.00, _("1 - No availability or support")
        TRACKING = 0.25, _("2 - Tracking potential use")
        DEVELOPING = 0.50, _("3 - Planning, piloting, and initial deployment")
        DEPLOYING = 0.75, _(
            "4 - Available/supported for parts of the institution")
        COMPLETE = 1.00, _("5 - Available/supported institution-wide")

    class ScoreCollaborationChoices(FloatChoices):
        NONE = 0.00, _("1 - No engagement with community collaboration")
        TRACKING = 0.25, _("2 - Exploring a community collaboration")
        DEVELOPING = 0.50, _("3 - Engaging a community collaboration")
        SUSTAINING = 0.75, _("4 - Supporting a community collaboration")
        LEADING = 1.0, _("5 - Leading a community collaboration")

    class ScoreSupportLevelChoices(FloatChoices):
        NONE = 0.00, _("1 - No existing service/support or awareness")
        UNRELIABLE = 0.25, _("2 - Very limited support and/or at risk")
        LIGHTS_ON = 0.50, _("3 - Minimal resources & commitment")
        BASIC = 0.75, _("4 - Basic sustained service/support & awareness")
        PREMIUM = 1.00, _("5 - Strong support, awareness, & commitment")

    score_deployment = models.FloatField(
        "Availability across institution",
        choices=ScoreDeploymentChoices.choices + [(None, "---")],
        default=None,
        blank=True,
        null=True,
        help_text="The level and breadth of availability across the institution for this service or resource."
        " This should take into account equitable access (including cost).",
    )

    score_supportlevel = models.FloatField(
        "Service operating level",
        choices=ScoreSupportLevelChoices.choices + [(None, "---")],
        default=None,
        blank=True,
        null=True,
        help_text="Represents the robustness, resilience, and sustainability of support for this service or resource.",
    )

    score_collaboration = models.FloatField(
        "Community engagement and collaboration",
        choices=ScoreCollaborationChoices.choices + [(None, "---")],
        default=None,
        blank=True,
        null=True,
        help_text="Represents the degree of engagement and collaboration, ranging from participation in community forums"
        " to regional projects to national collaborations. This should generally involve active engagement with other institutions.",
    )

    priority = models.PositiveSmallIntegerField(
        "Local Priority",
        default=None,
        null=True,
        blank=True,
        help_text=mark_safe("The priority, or importance of this question to your institution.\
            This can be used, e.g., to mark items you want to address in your strategic planning.\
                <br>Range is [1 to 99]  (1 is your top priority).\
                <br>This does not impact the calculated coverage.\
                <br>Clear or set to \"0\" if this is not a priority."),
    )

    work_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Private work notes for this question. Contents will not be included in the community datasets.",
    )

    is_modified = models.BooleanField(
        default=False,
        editable=False,
        help_text="Whether this answer has ever been modified from its original state (i.e. inherited value).",
    )
    not_applicable = models.BooleanField(
        "Question not applicable",
        default=False,
        help_text="Check ONLY this if this question is not at all applicable to your institution.",
    )

    class State(Enum):
        UNANSWERED = "unanswered"
        PARTIALLY_ANSWERED = "partially_answered"
        ANSWERED = "answered"
        NOT_APPLICABLE = "not_applicable"

    @property
    def state(self) -> "CapabilitiesAnswer.State":
        if self.not_applicable:
            return CapabilitiesAnswer.State.NOT_APPLICABLE

        answered = False
        incomplete_fields = list()

        for score in ("score_deployment", "score_collaboration", "score_supportlevel"):
            if getattr(self, score) is None:
                incomplete_fields.append(score)
            else:
                answered = True

        if answered:
            if incomplete_fields:
                return CapabilitiesAnswer.State.PARTIALLY_ANSWERED
            return CapabilitiesAnswer.State.ANSWERED
        else:
            return CapabilitiesAnswer.State.UNANSWERED

    def __str__(self):
        return str(self.question)