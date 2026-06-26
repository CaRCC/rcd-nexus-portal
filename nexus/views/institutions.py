from datetime import timedelta

from django.urls import reverse
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMultiAlternatives
from django.core.mail import send_mail

from django.template.loader import render_to_string
from django.http import HttpRequest
from django.shortcuts import redirect, render
from django.utils import timezone
from django.contrib.auth.decorators import login_required

from nexus.forms.institutions import (
    AffiliationRequestForm,
    InstitutionForm,
    NewInstitutionRequestForm,
)
from nexus.models.institutions import (
    AffiliationRequest,
    Institution,
    InstitutionAffiliation,
)

@login_required
def institution_request(request: HttpRequest):
    form = NewInstitutionRequestForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            form.instance.requester = request.user
            req = form.save()
            messages.success(
                request,
                f"Your request for '{req.name}' has been submitted. You will be notified when it is approved.",
            )
            review_link = f"{settings.BASE_URL+reverse('admin:nexus_newinstitutionrequest_changelist')}"

            send_mail(
                subject=f"CaRCC RCD Nexus portal Institution Request Submitted for {req.name}",
                message=f"A request to create a new Institution: {req.name} was just submitted by: {request.user}.\n\nAn admin needs to approve, reject, or ignore (delete) this request at: {review_link}",
                html_message=f'<p>Hello Support</p><p>A request to create a new Institution: {req.name} was just submitted by: {request.user}.</p><p>An admin needs to approve, reject, or ignore (delete) this request at: <a href="{review_link}">{review_link}</a>',
                from_email=settings.DEFAULT_FROM_EMAIL_USER+'@'+request.get_host(),
                recipient_list=[settings.SUPPORT_EMAIL],
            )
            return redirect("index")
        else:
            messages.error(request, "Please correct the errors below.")

    return render(
        request,
        "institutions/request.html",
        {
            "form": form,
            "institutions": Institution.objects.all(),
        },
    )


def institution_edit(request: HttpRequest, pk: int):
    if not request.user.is_staff and not InstitutionAffiliation.objects.filter(
        user=request.user, institution_id=pk
    ).exists():
        messages.error(request, "You are not affiliated with that institution.")
        return redirect("index")

    institution = Institution.objects.get(pk=pk)
    can_edit = institution.user_affiliations.filter(
        user=request.user, role=InstitutionAffiliation.Role.MANAGER
    ).exists()

    form = InstitutionForm(request.POST or None, instance=institution)

    if request.method == "POST" and can_edit:
        if form.is_valid():
            institution = form.save()
            messages.success(request, f"Updated institution '{institution}'.")
            return redirect("index")
        else:
            #print("Problem with Institution form. Data:",form.cleaned_data)
            messages.error(request, "Please correct the errors below.")

    return render(
        request,
        "institutions/edit.html",
        {
            "form": form,
            "can_edit": can_edit,
        },
    )

@login_required
def affiliation_request(request: HttpRequest, token=None):
    form = AffiliationRequestForm(request.POST or None)

    if token:
        try:
            aff_req = AffiliationRequest.objects.get(token=token, expires__gte=timezone.now(), user=request.user)
            if aff_req.approve():
                messages.success(request, f"Your affiliation with {aff_req.institution} has been confirmed.")
                send_mail(
                    subject="CaRCC RCD Nexus Institutional Affiliation Request Confirmed",
                    message=f"""
    {request.user}'s request to be affiliated with {aff_req.institution} via {aff_req.email} was approved.

    They can now create an assessment, so should probably be added to the capsModel-discuss list. 
    """,
                    from_email=settings.DEFAULT_FROM_EMAIL_USER+'@'+request.get_host(),
                    recipient_list=[settings.SUPPORT_EMAIL],
                    fail_silently=False,
                )
            else: 
                messages.error(request, f"Your affiliation with {aff_req.institution} already exists.")
        except AffiliationRequest.DoesNotExist:
            messages.error(request, "Invalid token.")

        return redirect("index")

    if request.method == "POST":
        if form.is_valid():
            email = form.cleaned_data["email"]
            name, domain = email.split("@")
            institution = Institution.objects.get(internet_domain=domain)
            if institution.has_cilogon_idp():
                messages.error(
                    request,
                    f"Access to {institution} is supported via CILogon. Please logout and login to this institution via CILogon.",
                )
                return redirect("index")
            aff_req, created = AffiliationRequest.objects.update_or_create(
                user=request.user,
                institution=institution,
                defaults={
                    "email": email,
                    "expires": timezone.now() + timedelta(days=7),
                },
            )
            #print(aff_req, aff_req.token, aff_req.expires)
            # We email the requester at their purported affiliation email, and let them approve the affiliation of another login
            req_link = request.build_absolute_uri(reverse("institutions:affiliation-request-approve", args=[aff_req.token]))
            email_in_html = render_to_string('institutions/affiliation_req_email.html', 
                                      {'user': request.user, 'institution':institution, 'email':email, 'req_link':req_link})
            msg = EmailMultiAlternatives(
                subject="CaRCC RCD Nexus Institution Affiliation Request",
                body=f"""Hello -

{request.user} has requested to be affiliated with {institution} via {email} in the CaRCC
Capabilities Model portal. If this is you, go ahead and approve the request. If this is not you,
please report this to the CaRCC Capabilities Model support team by replying to this email.

To approve this request, please visit the following link:

{req_link}
""",
                from_email=settings.DEFAULT_FROM_EMAIL_USER+'@'+request.get_host(),
                to=[email],
                reply_to=[settings.SUPPORT_EMAIL],  # Ensure a reply goes to the support team
                cc=[settings.SUPPORT_EMAIL],        # CC support for awareness
            )
            msg.attach_alternative(email_in_html, "text/html")
            msg.send()

            messages.success(
                request,
                f"A message has been sent to your institutional email address with instructions on how to complete your request.",
            )
            return redirect("index")
        else:
            messages.error(request, "Please correct the errors below.")

    return render(
        request,
        "institutions/affiliation_request.html",
        {
            "form": form,
        },
    )
