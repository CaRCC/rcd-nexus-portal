from django.conf import settings
from django.db import models


class IdentityProvider(models.Model):
    identifier = models.CharField(
        max_length=1000,
        unique=True,
        help_text="This should match an `entityID` listed in https://cilogon.org/include/idplist.xml",
    )
    name = models.CharField(
        max_length=1000,
        null=True,
    )
    institution = models.ForeignKey(
        "nexus.Institution",
        on_delete=models.RESTRICT,
        null=True,
        related_name="cilogon_idps",
    )
    active = models.BooleanField(
        default=True,
    )

    def __str__(self):
        return str(self.name)


class FederatedIdentity(models.Model):
    """
    An external user profile, such as from CILogon or some other federated identity provider.

    Links to an actual User, so one user can potentially be represented by many different logins.
    """

    identifier = models.CharField(
        max_length=1000,
        unique=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
    )
    provider = models.ForeignKey(
        IdentityProvider,
        on_delete=models.RESTRICT,
    )
    data = models.JSONField(
        blank=True,
    )

    def __str__(self):
        return f"{self.user} via {self.identifier} ({self.provider})"

    class Meta:
        verbose_name_plural = "Federated identities"

