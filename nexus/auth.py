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

                # Search for a matching existing institution, starting with the full domain and working up to the TLD.
                domain_parts = internet_domain.split(".")
                searched_part_count = len(domain_parts)
                while searched_part_count > 2:
                    idp.institution = models.Institution.objects.filter(internet_domain=".".join(domain_parts[-searched_part_count:])).first()
                    if idp.institution:
                        break
                    searched_part_count -= 1

                # No institution was found, so make one using the full domain name. Hopefully it wasn't already in IPEDS under a different domain name.
                if not idp.institution:
                    idp.institution = models.Institution.objects.create(
                        internet_domain=internet_domain,
                        name=idp.name or idp.identifier,
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
                profile.user.affiliations.get_or_create(institution=idp.institution)

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
