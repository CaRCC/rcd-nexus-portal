import secrets
import logging

from django.conf import settings
from django.contrib import admin
from django.db import models, transaction
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
import math

from .ipeds_classification import IPEDSMixin

logger = logging.getLogger(__name__)

class Institution(IPEDSMixin, models.Model):
    name = models.CharField(
        max_length=255,
    )
    country = models.CharField(
        max_length=255,
    )
    state_or_province = models.CharField(
        "State/Province",
        max_length=255,
        null=True,
        blank=True,
    )
    internet_domain = models.CharField(
        max_length=255,
        #unique=True,
    )

    demo_domains = ["internet2.edu", "sempercogito.com"]
    demo_ids = []

    def getDemoIDList() :
        if len(Institution.demo_ids) > 0:
            return Institution.demo_ids
        for d in Institution.demo_domains:
            try:
                institution = Institution.objects.get(internet_domain__endswith=d)
            except Institution.DoesNotExist:
                logger.error(f"getDemoIDList(): No institution found for domain: [{d}].")
            except Institution.MultipleObjectsReturned:
                logger.error(f"getDemoIDList(): Multiple institutions found for domain: [{d}], only adding first.")
                institution = Institution.objects.get(internet_domain__endswith=d).first()
            Institution.demo_ids.append(institution.id)
            # print(f'getDemoIDList() init: Added institution (id=[{institution.id}] for domain:[{d}]')

        return Institution.demo_ids


    undergrad_pop = models.PositiveIntegerField(
        "Undergraduate Population",
        null=True,
        blank=True,
    )

    grad_pop = models.PositiveIntegerField(
        "Graduate Population",
        null=True,
        blank=True,
    )

    student_pop = models.PositiveIntegerField(
        "Student Population",
        null=True,
        blank=True,
    )

    def student_thous(self):
        if self.student_pop is None :
            return "(Unknown)"
        fmt = "{:.1f} K ({:.1f} K Undergrad, {:.1f} K Grad)"
        return fmt.format(self.student_pop/1000, self.undergrad_pop/1000, self.grad_pop/1000)

    research_expenditure = models.PositiveBigIntegerField(
        "Research Expenditures",
        null=True,
        blank=True,
    )

    def research_mdollars(self):
        if self.research_expenditure is None :
            return "(Unknown)"
        if self.research_expenditure < 1000000:
            fmt = "${:,} Thousand"
            divisor = 1000
        else:
            fmt = "${:,} Million"
            divisor = 1000000
        return fmt.format(math.floor(round(self.research_expenditure/divisor)))

    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="InstitutionAffiliation",
        related_name="institutions",
    )

    list_as_contributor = models.BooleanField(
        default=True,
        help_text="Whether a representative of this institution has agreed to be listed as a contributor to the RCD Nexus.",
    )

    @admin.display(boolean=True, description="Has CILogon IDP")
    def has_cilogon_idp(self):
        return False  # TODO just for testing email
        # return self.cilogon_idps.exists()

    def __str__(self):
        return self.name

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "country", "state_or_province"],
                name="unique_institution",
            ),
        ]


class NewInstitutionRequest(models.Model):
    name = models.CharField(
        max_length=255,
    )
    country = models.CharField(
        max_length=255,
    )
    state_or_province = models.CharField(
        "State/Province",
        max_length=255,
        null=True,
        blank=True,
    )
    internet_domain = models.CharField(
        max_length=255,
        unique=False,
    )
    comment = models.TextField(
        null=True,
        blank=True,
    )
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="+",
    )
    created = models.DateTimeField(
        auto_now_add=True,
    )

    def approve(self, request):
        user = self.requester.name()
        with transaction.atomic():
            institution = Institution.objects.create(
                name=self.name,
                country=self.country,
                state_or_province=self.state_or_province,
                internet_domain=self.internet_domain,
            )
            InstitutionAffiliation.objects.create(
                institution=institution,
                user=self.requester,
                role=InstitutionAffiliation.Role.MANAGER,
            )
            self.delete()

        inst_link = settings.BASE_URL+reverse("institutions:edit", args=[institution.pk])
        email_in_html = render_to_string('institutions/inst_added_email.html', 
                            {'user': user, 'institution': institution, 'inst_link':inst_link})
        msg = EmailMultiAlternatives(
            subject=f"Institution added to the CaRCC RCD Nexus portal",
            body=f"""Hello {user} - 
        
Your institution request for {institution} has been approved, and you have been added as a manager.

You can manage it at: {inst_link}

Please add as much institutional information as possible to improve the community datasets.

You may now begin using the CaRCC Capabilities Model assessment tools for your institution!
""",
            from_email=settings.DEFAULT_FROM_EMAIL_USER+'@'+request.get_host(),
            to=[self.requester.email],
            cc=[settings.SUPPORT_EMAIL],
        )
        msg.attach_alternative(email_in_html, "text/html")
        msg.send()

        return institution

    def reject_dupe(self, request):
        user = self.requester.name()
        institution = self.name
        supportEmail = settings.SUPPORT_EMAIL
        email_in_html = render_to_string('institutions/inst_rejected_email.html', 
                            {'user': user, 'institution': institution, 'support':supportEmail})
        email_as_text = f"""Hello {user} - 
                
Your institution request for {institution} has been denied, as we already have an institution record for that institution. 

Please respond to this email or reach out to us at {supportEmail} if you have any questions. 
"""
        msg = EmailMultiAlternatives(
            subject=f"Request for new institution on the CaRCC RCD Nexus portal was denied",
            body=email_as_text,
            from_email=supportEmail,
            to=[self.requester.email],
            cc=[supportEmail],
        )
        msg.attach_alternative(email_in_html, "text/html")
        msg.send()

        self.delete()
        
        return institution  # Note this is just the name string
      
    def __str__(self):
        return f"{self.name} (by {self.requester})"


class InstitutionAffiliation(models.Model):
    institution = models.ForeignKey(
        Institution,
        on_delete=models.CASCADE,
        related_name="user_affiliations",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="affiliations",
    )

    class Role(models.TextChoices):
        AFFILIATE = "affiliate", "Affiliate"
        MANAGER = "manager", "Manager"

    role = models.CharField(
        max_length=64,
        choices=Role.choices,
        default=Role.AFFILIATE,
    )

    def __str__(self):
        return f"{self.user} is a {self.role} for {self.institution}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "institution"],
                name="unique_institution_affiliation",
            ),
        ]


class AffiliationRequest(models.Model):
    """
    A request to add an affiliate a non-institutional user (e.g. Google account) to an institution.
    """

    class QuerySet(models.QuerySet):
        def create(self, *args, **kwargs):
            kwargs.setdefault("token", secrets.token_urlsafe(48))
            return super().create(*args, **kwargs)

        def filter_valid(self):
            return self.filter(expires__gt=timezone.now())

    objects = QuerySet.as_manager()

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="+",
    )
    institution = models.ForeignKey(
        "nexus.Institution",
        on_delete=models.CASCADE,
        related_name="affiliation_requests",
    )
    email = models.EmailField()
    token = models.CharField(
        max_length=64,
        unique=True,
    )
    expires = models.DateTimeField()

    def approve(self):
        # Check whether this affiliation has already been created (e.g., directly by a manager)
        if InstitutionAffiliation.objects.filter(
            user=self.user, institution_id=self.institution.pk).exists():
            self.delete()   # Just toss this one and ignore
            return False
        with transaction.atomic():
            InstitutionAffiliation.objects.create(
                user=self.user,
                institution=self.institution,
                role=InstitutionAffiliation.Role.AFFILIATE,
            )
            self.delete()
        return True

    def __str__(self):
        return f"{self.user} -> {self.institution} (via {self.email})"
