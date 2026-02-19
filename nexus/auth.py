import re
import xml.etree.ElementTree

import requests
from django.core.exceptions import SuspiciousOperation
from mozilla_django_oidc.auth import OIDCAuthenticationBackend
from django.contrib import messages
from django.conf import settings
from django.core.mail import send_mail

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

    invalid_IDPs = {"http://github.com/login/oauth/authorize":"GitHub",
                             "http://orcid.org/oauth/authorize":"ORCID",
                             "https://access-ci.org/idp":"ACCESS-CI",
                             "https://proxyidp.es.net/satosafrontend/proxy.xml":"ESNet",}

    def authenticate(self, request, **kwargs):
        try:
            return super().authenticate(request, **kwargs)
        except InvalidClaimsError as e:
            badIDP = CILogonOIDCAuthenticationBackend.invalid_IDPs[e.claims["idp"]]
            if badIDP:
                messages.error(request, f'{badIDP} login is not currently supported. Please use your institutional login, or a supported social login such as Google.')
            else:
                messages.error(request, "Invalid identity provider. If it is your institution, please contact RCD Nexus support.")

    def verify_claims(self, claims):
        # print(f'Verify_claims: {claims}')
        if claims["idp"] in CILogonOIDCAuthenticationBackend.invalid_IDPs.keys():
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
        # print(f'CILogon backend get or create user: {claims["email"]} for idp: {idp.name}')
        if not idp.institution:
            try:
                details = get_cilogon_idp_details(idp.identifier)
                internet_domain = domain_pattern.match(details["Home_Page"]).groups()[0]

                # Search for a matching existing institution, starting with the full domain and working up to the TLD.
                domain_parts = internet_domain.split(".")
                searched_part_count = len(domain_parts)
                while searched_part_count >= 2:
                    idp.institution = models.Institution.objects.filter(internet_domain=".".join(domain_parts[-searched_part_count:])).first()
                    if idp.institution:
                        break
                    searched_part_count -= 1

                # No institution was found, so make one using the full domain name. Hopefully it wasn't already in IPEDS under a different domain name.
                if not idp.institution:
                    send_mail(
                        subject=f"Nexus Portal creating new Institution",
                        message=f'CILogon backend: No institution found for idp internet_domain: {internet_domain} for login by: {claims.get("email")}; creating one.',
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[settings.SUPPORT_EMAIL],
                    )
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
            # we map email to their username on create, but historically did not convert to lowercase, so use the email 
            # to find the user, but allow case-insensitive match
            profile.user, created = models.User.objects.get_or_create(
                username__iexact=claims["email"],
                defaults={
                    "email": claims["email"],               # leave their email as they specified it
                    "username": claims["email"].lower(),    # force to lower for the username
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
