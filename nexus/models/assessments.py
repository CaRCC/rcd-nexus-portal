"""
Common assessment definitions/metadata. For actual assessments models, see:
    - nexus.models.capmodel
"""

from django.conf import settings
from django.db import models


class AssessmentBase(models.Model):
    """
    Abstract Assessment with common metadata that is used to implement Capabilities assessment, et al.
    """

    class Meta:
        abstract = True

    update_time = models.DateTimeField(
        auto_now=True, help_text="When the assessment was most recently updated."
    )
    update_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="+",
        editable=False,
        help_text="The user that most recently updated the assessment.",
    )

    class ReviewStatusChoices(models.TextChoices):
        NOT_SUBMITTED = "not_submitted", "Not yet submitted"
        PENDING = "pending", "Review pending"
        APPROVED = "approved", "Approved"
        DENIED = "denied", "Denied"

    review_status = models.CharField(
        max_length=64,
        choices=ReviewStatusChoices.choices,
        default=ReviewStatusChoices.NOT_SUBMITTED,
    )
    review_time = models.DateTimeField(
        editable=False,
        null=True,
        help_text="When the assessment status was last updated by an administrator",
    )
    review_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="+",
        editable=False,
        help_text="The Nexus data steward that last reviewed this assessment.",
    )
    review_note = models.TextField(
        null=True,
        blank=True,
        help_text="An explanation of why the assessment was denied, etc.",
    )

    @property
    def is_frozen(self) -> bool:
        return self.review_status == AssessmentBase.ReviewStatusChoices.APPROVED
