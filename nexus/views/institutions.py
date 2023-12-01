from datetime import timedelta

from django.urls import reverse
from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.http import HttpRequest
from django.shortcuts import redirect, render
from django.utils import timezone

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
            send_mail(
                subject=f"RCD Nexus Institution Request Submitted for {req.name}",
                message=f"A request to create a new Institution: {req.name} was just submitted by: {request.user}.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.CURATOR_EMAIL],
            )
            return redirect("index")
        else:
            messages.error(request, "Please correct the errors below.")

    return render(
        request,
        "institutions/request.html",
        {
            "form": form,
        },
    )


def institution_edit(request: HttpRequest, pk: int):
    if not InstitutionAffiliation.objects.filter(
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
            messages.error(request, "Please correct the errors below.")

    return render(
        request,
        "institutions/edit.html",
        {
            "form": form,
            "can_edit": can_edit,
        },
    )


def affiliation_request(request: HttpRequest, token=None):
    form = AffiliationRequestForm(request.POST or None)

    if token:
        try:
            aff_req = AffiliationRequest.objects.get(token=token, expires__gte=timezone.now(), user=request.user)
            aff_req.approve()
            messages.success(request, f"Your affiliation with {aff_req.institution} has been confirmed.")
            send_mail(
                subject="RCD Nexus Affiliation Request Confirmed",
                message=f"""
{request.user}'s request to be affiliated with {aff_req.institution} via {aff_req.email} was approved.

They can now create an assessment, so should probably be added to the capsModel-discuss list. 
""",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.SUPPORT_EMAIL],
                fail_silently=False,
            )
        except AffiliationRequest.DoesNotExist:
            messages.error(request, "Invalid token.")

        return redirect("index")

    if request.method == "POST":
        if form.is_valid():
            email = form.cleaned_data["email"]
            name, domain = email.split("@")
            institution = Institution.objects.get(internet_domain=domain)
            aff_req, created = AffiliationRequest.objects.update_or_create(
                user=request.user,
                institution=institution,
                defaults={
                    "email": email,
                    "expires": timezone.now() + timedelta(days=7),
                },
            )
            print(aff_req, aff_req.token, aff_req.expires)
            send_mail(
                subject="RCD Nexus Affiliation Request",
                message=f"""
{request.user} has requested to be affiliated with {institution} via {email}.

To approve this request, please visit the following link:

{request.build_absolute_uri(reverse("institutions:affiliation-request-approve", args=[aff_req.token]))}
""",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )

            messages.success(
                request,
                f"An email has been sent to '{email}' with instructions on how to complete your request.",
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
