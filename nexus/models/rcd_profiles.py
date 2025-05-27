import logging
import secrets

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.query import QuerySet
from django.utils import timezone
from django.utils.text import slugify
from django.utils.safestring import mark_safe
from nexus.models.capmodel import CapabilitiesAssessment

from nexus.utils.time import next_week

logger = logging.getLogger(__name__)


class RCDProfile(models.Model):
    class ArchiveManager(models.Manager):
        def create(self, *args, **kwargs):
            """
            Create a new RCDProfile for an institution.
            """
            profile = super().create(*args, **kwargs)
            profile.memberships.create(
                user=profile.created_by, role=RCDProfileMember.Role.SUBMITTER
            )
            return profile

        def copy(self, existing, created_by):
            """
            Prepopulate a profile (but not an assessment), with data from a previous profile.
            """
            profile = self.create(
                institution=existing.institution,
                institution_subunit=existing.institution_subunit,
                mission=existing.mission,
                structure=existing.structure,
                org_chart=existing.org_chart,
                profile_reason=existing.profile_reason,
                comments=f"Initialized using institutional metadata from {existing}.",
                created_by=created_by,
            )

            # This is the old flow but not assessment import is decoupled
            #if hasattr(existing, "capabilities_assessment"):
            #    profile.capabilities_assessment = apps.get_model(
            #        "nexus", "CapabilitiesAssessment"
            #    ).objects.copy(existing.capabilities_assessment, profile=profile)

            profile.save()
            return profile

        def filter_can_view(self, user):
            return self.filter(
                models.Q(memberships__user=user) | (
                    models.Q(institution__in=user.institutions.all())
                    & models.Q(open_access=True)
                )
            ).distinct()

        def filter_can_edit(self, user):
            return self.filter(
                memberships__user=user,
                memberships__role__in={
                    RCDProfileMember.Role.CONTRIBUTOR,
                    RCDProfileMember.Role.MANAGER,
                    RCDProfileMember.Role.SUBMITTER,
                },
            )

        def filter_can_manage(self, user):
            return self.filter(
                memberships__user=user,
                memberships__role__in={
                    RCDProfileMember.Role.MANAGER,
                    RCDProfileMember.Role.SUBMITTER,
                },
            )

        def filter_can_submit(self, user):
            return self.filter(
                memberships__user=user,
                memberships__role__in={
                    RCDProfileMember.Role.SUBMITTER,
                },
            )

    class Manager(ArchiveManager):
        def get_queryset(self) -> QuerySet:
            return super().get_queryset().exclude(archived=True)

    class Meta:
        verbose_name = "RCD profile"

    objects_archive = ArchiveManager()
    objects = Manager()

    institution = models.ForeignKey(
        "nexus.Institution",
        on_delete=models.RESTRICT,
        related_name="profiles",
    )

    class MissionChoices(models.TextChoices): 
        RESEARCHESSENTIAL = "rsrchess", mark_safe("<b>Research Essential</b>: Research is the primary or exclusive mission, \
            and teaching does not significantly factor into faculty and institutional success \
                                                  (Research Labs, National Supercomputing Centers, etc.).")
        RESEARCHFAVORED = "rsrchfav", mark_safe("<b>Research Favored</b>: Research and teaching are the primary missions, \
            but research is what really drives faculty and institutional success (e.g., Research-driven Universities).")
        BALANCED = "balanced", mark_safe("<b>Balanced</b>: Research and teaching are both primary missions, \
            and they are equally important for faculty and institutional success.")
        TEACHINGFAVORED = "teachfav", mark_safe("<b>Teaching Favored</b>: Teaching is the primary mission, \
                                                but faculty research is rewarded.")
        TEACHINGESSENTIAL = "teachess", mark_safe("<b>Teaching Essential</b>: Teaching is the primary mission, \
            and faculty research does not factor heavily in faculty and institutional success.")
        __empty__ = "Unknown"


    def getShortMissionChoice(label):
        #The Choices all have the main label marked in <b> tags, at the start. We just extract that
        return label[3:label.find("</b>")]

    mission = models.CharField(
        "Institutional Mission",
        max_length=64,
        choices=MissionChoices.choices,
        default=None,
        null=True,      # Allow this to be missing, especilaly on import
        blank=False,    # Require user to set one
        help_text="Select the option that best describes your institution's mission.",
    )

    class StructureChoices(models.TextChoices):
        STANDALONE = "standalone", "Primarily within a central RCD/HPC group"
        EMBEDDED = "embedded", "Embedded within a single department or school"
        DECENTRALIZED = (
            "decentralized",
            "Decentralized collaboration among several departments, schools, etc.",
        )
        NONE = "none", "No organized RCD support program currently exists"

    structure = models.CharField(
        "RCD organizational model",
        max_length=32,
        choices=StructureChoices.choices,
        #default=StructureChoices.NONE,
        null=True,
        blank=False,
        help_text="Select the option that best describes how your institution's RCD services and staff are organized.",
    )

    class OrgChartChoices(models.TextChoices):
        INFOTECH = "infotech", "Information technology (e.g., CIO)"
        RESEARCH = "research", "Research (e.g., VPR)"
        ACADEMIA = "academic", "Academic leadership (e.g., Provost or a Dean)"
        INSTITUTE = "institute", "Academic/Research Institute or Center"
        # MEDICAL = "medical", "Health sciences/Medical school"  This is a scoping issue, not an org model
        OTHER = "other", "Other"
         # NONE = "none", "Not applicable"  This is covered under Other, and simplifies things to omit it
        __empty__ = "Unknown"


    org_chart = models.CharField(
        "Reporting structure",
        max_length=32,
        choices=OrgChartChoices.choices,
        null=True,
        blank=False,
        help_text=mark_safe("Select the option that best describes where within the institution your RCD program ultimately reports.\
              <br/>If 'Other', please explain in the comment section below."),
    )

    institution_subunit = models.CharField(
        "Organizational scope",
        max_length=255,
        null=True,
        blank=True,
        help_text=mark_safe("<em>(Optional)</em> If the scope of this profile is RCD support at the entire institution \
            (the common case, and preferred use of the Capabilities Model), you can <b>leave this blank</b>.<br/> \
            If you are completing an assessment for just one part of your institution, \
            enter the name of the institutional subunit (e.g. 'College of Engineering', 'School of Medicine', 'Center for ...')."),
    )
    year = models.PositiveIntegerField(
        default=settings.RCD_DEFAULT_YEAR,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        related_name="profiles_created",
    )

    class ProfileReasonChoices(models.TextChoices):
        RCDCMASSESS = "rcdcmassess", "To create a Capabilities Model assessment"
        SIMPLE = "simple", "Just creating a simple profile for now (I'm exploring)"
        OTHER = "other", "Other"

    profile_reason = models.CharField(
        "Reason for creating profile",
        max_length=32,
        choices=ProfileReasonChoices.choices,
        default=ProfileReasonChoices.RCDCMASSESS,
        help_text=mark_safe("If you are creating this profile other than to complete a Capabilities Model assessment (the default), \
            what is your reason for creating this profile (i.e., how do you intend to use it)? \
                <br/>If \"Other\", please explain in the comment section below."),
    )

    comments = models.TextField(
        blank=True,
        null=True,
        help_text="Any additional information about RCD support at your institution.",
    )

    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="RCDProfileMember",
        related_name="rcd_profiles",
    )

    open_access = models.BooleanField(
        default=True,
        blank=True,
        help_text="Open access profiles are visible to all users belonging to its primary institution (recommended).",
    )

    archived = models.BooleanField(
        default=False,
        help_text="Archived profiles are hidden from view, but can be restored.",
    )

    survey = models.OneToOneField(
        "PostCompletionSurvey",
        on_delete=models.CASCADE,
        related_name="profile",
        null=True, 
        blank=True,
    )


    def __str__(self):
        archived = "[ARCHIVED] " if self.archived else ""

        if not hasattr(self, "capabilities_assessment"):
            atype = ""
        elif self.capabilities_assessment.assessment_type == CapabilitiesAssessment.AssessmentTypeChoices.ESSENTIAL:
            atype = " Essential"
        elif self.capabilities_assessment.assessment_type == CapabilitiesAssessment.AssessmentTypeChoices.CYOJ:
            atype = " Custom"
        else: 
            atype = " Full"
        subunit = (
            f"({self.institution_subunit}) at " if self.institution_subunit else ""
        )
        return f"{archived}{subunit}{self.institution} ({self.year}{atype})"

class SurveyReasonChoices(models.TextChoices):
    BENCHMARKING = "benchmarking", "Benchmarking of current service offerings."
    STRATPLAN = "stratplan", "As part of (or an input to) Strategic Planning."
    UNDERSTANDING = "understanding", "To better understand common practices."
    OTHER = "other", "Other"

class SurveyReason(models.Model):
    reason = models.CharField(
                max_length=16,
                choices = SurveyReasonChoices.choices,
    )
    def __str__(self):
        return SurveyReasonChoices(self.reason).label

class PostCompletionSurvey(models.Model):
    labor_hours = models.PositiveIntegerField(
        "About how many labor hours went into completing the assessment at your institution?",
        help_text="Please include meetings (hours X the # of attendees) as well as individuals' effort to complete the assessment.",
        null=True,
        blank=False,
        validators=[MaxValueValidator(400), MinValueValidator(1)],
    )

    reasons = models.ManyToManyField(SurveyReason)

    class SurveyRepeatChoices(models.TextChoices):
        NEXTYR = "nextyr", "Next year."
        TWO_THREE = "two_three", "In two or three years."
        FOUR_FIVE = "four_five", "In 4 or 5 years."
        UNLIKELY = "unlikely", "Unlikely to complete another one in future"

    repeat = models.CharField(
        "How soon would your institution likely complete a future Capabilities Model Assessment?",
        help_text="E.g., to assess progress on areas for improvement.",
        max_length=32,
        default=None,
        blank=False,
        choices=SurveyRepeatChoices.choices,
    )

    class SurveyNPSChoices(models.IntegerChoices):
        NPS_0 = 0, "0 Not at all Likely"
        NPS_1 = 1, "1"
        NPS_2 = 2, "2"
        NPS_3 = 3, "3"
        NPS_4 = 4, "4"
        NPS_5 = 5, "5"
        NPS_6 = 6, "6"
        NPS_7 = 7, "7"
        NPS_8 = 8, "8"
        NPS_9 = 9, "9"
        NPS_10 = 10, "10 Extremely Likely"

    nps = models.PositiveIntegerField(
        "Based upon your experience, how likely are you to recommend the Capabilities Model Assessment tool to other institutions?",
        default=None,
        blank=False,
        choices=SurveyNPSChoices.choices,
    )

class RCDProfileMember(models.Model):
    profile = models.ForeignKey(
        RCDProfile,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="rcd_profile_memberships",
    )

    class Role(models.TextChoices):
        VIEWER = "viewer", "Viewer"
        CONTRIBUTOR = "contributor", "Contributor"
        MANAGER = "manager", "Manager"
        SUBMITTER = "submitter", "Submitter"

    role = models.CharField(
        max_length=32,
        choices=Role.choices,
        default=Role.VIEWER,
    )

    class Meta:
        verbose_name = "profile member"
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "user"],
                name="unique_profile_member",
            )
        ]


class RCDProfileMemberInvite(models.Model):
    class Manager(models.Manager):
        def create(self, *args, **kwargs):
            if "token" not in kwargs:
                kwargs["token"] = secrets.token_urlsafe(48)
            return super().create(*args, **kwargs)

    class QuerySet(models.QuerySet):
        def filter_valid(self):
            return self.filter(expire_time__gt=timezone.now())

    objects = Manager.from_queryset(QuerySet)()

    profile = models.ForeignKey(
        RCDProfile,
        on_delete=models.CASCADE,
        related_name="invitations",
    )
    role = models.CharField(
        max_length=32,
        choices=RCDProfileMember.Role.choices,
        default=RCDProfileMember.Role.CONTRIBUTOR,
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="+",
    )
    expire_time = models.DateTimeField(default=next_week)
    token = models.CharField(
        max_length=64,
        unique=True,
    )

    @property
    def is_expired(self):
        return timezone.now() > self.expire_time

    def invite(self, user) -> (RCDProfileMember, bool):
        return self.profile.memberships.get_or_create(
            user=user,
            defaults=dict(role=self.role),
        )


class RCDProfileMemberRequest(models.Model):
    """
    Tracks which Users have outstanding requests to join RCDProfiles as contributors.
    """

    profile = models.ForeignKey(
        RCDProfile,
        on_delete=models.CASCADE,
        related_name="membership_requests",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="+",
    )

    def approve(self):
        """
        Adds the user to the profile as a contributor, and deletes this Request from the database.
        """
        membership = self.profile.memberships.get_or_create(
            user=self.requested_by,
            defaults=dict(role=RCDProfileMember.Role.CONTRIBUTOR),
        )
        self.delete()
        return membership

    def deny(self):
        """
        Delete this Request without granting membership to the user.
        """
        self.delete()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "requested_by"],
                name="%(app_label)s_%(class)s_unique",
            )
        ]
