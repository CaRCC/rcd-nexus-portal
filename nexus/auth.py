import re
import xml.etree.ElementTree

import requests
from django.core.exceptions import SuspiciousOperation
from mozilla_django_oidc.auth import OIDCAuthenticationBackend
from django.contrib import messages

from nexus import models

domain_pattern = re.compile(r"^(?:https?:\/\/)?(?:[^@\/\n]+@)?(?:www\.)?([^:\/?\n]+)")


class InvalidClaimsError(Exception):
    def __init__(self, claims) -> None:
        super().__init__("Invalid claims received from IDP")
        self.claims = claims

class CILogonOIDCAuthenticationBackend(OIDCAuthenticationBackend):
    """
    Overrides some default `mozilla_django_oidc` behaviors to work better with
    CHPC and CILogon.
    """

    def authenticate(self, request, **kwargs):
        try:
            return super().authenticate(request, **kwargs)
        except InvalidClaimsError as e:
            if e.claims["idp"] == "http://orcid.org/oauth/authorize":
                messages.error(request, "ORCID login is not currently supported. Please use your institutional login, or a supported social login such as Google.")
            elif e.claims["idp"] == "http://github.com/login/oauth/authorize":
                messages.error(request, "GitHub login is not currently supported. Please use your institutional login, or a supported social login such as Google.")
            else:
                messages.error(request, "Invalid identity provider. If it is your institution, please contact RCD Nexus support.")

    def verify_claims(self, claims):
        if claims["idp"] in {"http://github.com/login/oauth/authorize", "http://orcid.org/oauth/authorize"}:
            return False
            
        return super().verify_claims(claims)
    
    def get_or_create_user(self, access_token, id_token, payload):
        claims = self.get_userinfo(access_token, id_token, payload)

        if not self.verify_claims(claims):
            raise InvalidClaimsError(claims)

        idp, created = models.IdentityProvider.objects.get_or_create(
            identifier=claims["idp"],
            defaults={"name": claims.get("idp_name", None)},
        )
        if not idp.institution:
            try:
                details = get_cilogon_idp_details(idp.identifier)
                internet_domain = domain_pattern.match(details["Home_Page"]).groups()[0]
                idp.institution, created = models.Institution.objects.get_or_create(
                    internet_domain=internet_domain,
                    defaults={"name": idp.name or idp.identifier},
                )
            except ValueError:
                pass

            idp.save()

        profile, created = models.FederatedIdentity.objects.update_or_create(
            identifier=claims["sub"],
            defaults={
                "provider": idp,
                "data": claims,
            },
        )

        if profile.user == None:
            profile.user, created = models.User.objects.get_or_create(
                email=claims["email"],
                defaults={
                    "username": claims["email"],
                    "first_name": claims.get("given_name"),
                    "last_name": claims.get("family_name"),
                },
            )
            profile.save()
            if idp.institution:
                profile.user.affiliations.create(institution=idp.institution)

        return profile.user


def get_cilogon_idp_details(identifier) -> dict:
    try:
        root = xml.etree.ElementTree.fromstring(
            requests.get("https://cilogon.org/include/idplist.xml").content
        )
        idp = root.find(f'.//idp/[@entityID="{identifier}"]')
        return {elem.tag: elem.text for elem in idp.iter()}
    except:
        raise ValueError(f"Could not find IDP details for {identifier}")
