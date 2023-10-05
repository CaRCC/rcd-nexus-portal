import logging
import secrets

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.query import QuerySet
from django.utils import timezone
from django.utils.text import slugify
from django.utils.safestring import mark_safe

from nexus.utils.time import next_week

logger = logging.getLogger(__name__)


class RCDProfile(models.Model):
    class ArchiveManager(models.Manager):
        def create(self, *args, **kwargs):
            """
            Create a new RCDProfile, and associated assessments, for an institution.
            """
            profile = super().create(*args, **kwargs)
            profile.memberships.create(
                user=profile.created_by, role=RCDProfileMember.Role.SUBMITTER
            )
            return profile

        def copy(self, existing, created_by):
            """
            Prepopulate a profile, and associated assessments, with data from a previous profile.
            """
            profile = self.create(
                institution=existing.institution,
                institution_subunit=existing.institution_subunit,
                structure=existing.structure,
                org_chart=existing.org_chart,
                profile_reason=existing.profile_reason,
                comments=existing.comments,
                created_by=created_by,
            )

            # TODO is this best flow? Or should assessment import be decoupled
            if hasattr(existing, "capabilities_assessment"):
                profile.capabilities_assessment = apps.get_model(
                    "nexus", "CapabilitiesAssessment"
                ).objects.copy(existing.capabilities_assessment, profile=profile)

            profile.save()
            return profile

        def filter_can_view(self, user):
            return self.filter(
                models.Q(institution__in=user.institutions.all())
                | models.Q(memberships__user=user)
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
            and teaching does not significantly factor into faculty and institutional success.")
        RESEARCHFAVORED = "rsrchfav", mark_safe("<b>Research Favored</b>: Research and teaching are the primary missions, \
            but research is what really drives faculty and institutional success.")
        BALANCED = "balanced", mark_safe("<b>Balanced</b>: Research and teaching are both primary missions, \
            and they are equally important for faculty and institutional success.")
        TEACHINGFAVORED = "teachfav", mark_safe("<b>Teaching Favored</b>: Teaching is the primary mission, \
                                                but faculty research is rewarded.")
        TEACHINGESSENTIAL = "teachess", mark_safe("<b>Teaching Essential</b>: Teaching is the primary mission, \
            and faculty research does not factor heavily in faculty and institutional success.")

    mission = models.CharField(
        "Institutional Mission",
        max_length=64,
        choices=MissionChoices.choices,
        default=None,
        null=True,      # Allow this to be missing, especilaly on import
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
        RCDCMASSESS = "rcdcmassess", "To create an RCD Capabilities Model assessment"
        SIMPLE = "simple", "Just creating a simple profile for now (I'm exploring)"
        OTHER = "other", "Other"

    profile_reason = models.CharField(
        "Reason for creating profile",
        max_length=32,
        choices=ProfileReasonChoices.choices,
        default=ProfileReasonChoices.RCDCMASSESS,
        help_text=mark_safe("If you are creating this profile other than to complete an RCD Capabilities Model assessment (the default), \
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

    archived = models.BooleanField(
        default=False,
        help_text="Archived profiles are hidden from view, but can be restored.",
    )

    def __str__(self):
        archived = "[ARCHIVED] " if self.archived else ""
        subunit = (
            f"({self.institution_subunit}) at " if self.institution_subunit else ""
        )
        return f"{archived}{subunit}{self.institution} ({self.year})"


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
