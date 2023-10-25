import logging
import re

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseNotModified,
    HttpResponseRedirect,
)
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.safestring import mark_safe

from nexus.forms import RCDProfileForm, RCDProfileMemberInviteForm
from nexus.models import (
    RCDProfile,
    RCDProfileMember,
    RCDProfileMemberInvite,
    RCDProfileMemberRequest,
)
from nexus.utils.navtree import NavNode

logger = logging.getLogger(__name__)

roles = RCDProfileMember.Role
view_roles = {roles.VIEWER, roles.CONTRIBUTOR, roles.MANAGER, roles.SUBMITTER}
edit_roles = {roles.CONTRIBUTOR, roles.MANAGER, roles.SUBMITTER}
manage_roles = {roles.MANAGER, roles.SUBMITTER}
submit_roles = {roles.SUBMITTER}


def index(request):
    if request.user.is_authenticated:
        if "profile_invite_token" in request.session:
            return redirect("rcdprofile:accept-invite")

        return rcd_profile_default(request)

    return render(request, "index.html")


def navtree(profile, current_labels=None):
    """
    Return a navigation tree for RCD Profile pages. Node labels matching `current_labels` will be highlighted.
    """
    tree = NavNode(
        children=[
            NavNode(
                label=str(profile),
                link=reverse("rcdprofile:detail", kwargs={"pk": profile.pk}),
                children=[
                    NavNode(
                        label=navtree.CONTRIBUTORS,
                        link=reverse(
                            "rcdprofile:members",
                            kwargs={"pk": profile.pk},
                        ),
                    ),
                    NavNode(
                        label=navtree.CAPABILITIES,
                        link=reverse(
                            "capmodel:assessment", kwargs={"profile_id": profile.pk}
                        ),
                    ),
                ],
            )
        ]
    )

    # TODO can build the navtree by appending children based on request user's access, e.g. only append "Contributors" if user is a Manager

    if current_labels:
        tree.set_current(current_labels)

    return tree


navtree.CONTRIBUTORS = "Manage Contributors"
navtree.CAPABILITIES = "RCD Capabilities Model Assessment"


def access_profile(request, pk, action="view", allow_archive=False):
    if not request.user.is_authenticated:
        raise PermissionDenied
    
    profiles = RCDProfile.objects if not allow_archive else RCDProfile.objects_archive
    profile = profiles.get(pk=pk)

    if request.user.is_staff:
        return profile

    match action:
        case "view":
            allowed = profile.users.filter(pk=request.user.pk).exists() or (profile.open_access and profile.institution.users.filter(pk=request.user.pk).exists())
        case "edit":
            allowed = profile.memberships.filter(user=request.user, role__in=edit_roles).exists()
        case "manage":
            allowed = profile.memberships.filter(user=request.user, role__in=manage_roles).exists()
        case "submit":
            allowed = profile.memberships.filter(user=request.user, role__in=submit_roles).exists()
        case _:
            messages.error(request, f"Invalid action '{action}'")

    if not allowed:
        join_note = (
            f"<a href='{reverse('rcdprofile:request-access', kwargs={'pk': pk})}'>Request access</a>"
            if RCDProfile.objects.filter_can_view(request.user).filter(pk=pk).exists()
            else ""
        )
        raise PermissionDenied(
            mark_safe(
                f"""You are not permitted to {action} this RCD Profile.
                {join_note}
                """
            )
        )
    
    return profile


def rcd_profile_default(request):
    """
    Redirect to the current 'default' RCD Profile for the logged-in user, according to heuristics.
    """
    if not request.user.is_authenticated:
        return redirect("index")

    # Get the first profile from the current year where the user is a contributor
    membership = request.user.rcd_profile_memberships.filter(
        profile__year=settings.RCD_DEFAULT_YEAR, role__in=edit_roles
    ).first()
    if membership is None:
        # Otherwise, get the first profile from the current year where the user is a viewer
        membership = request.user.rcd_profile_memberships.filter(
            profile__year=settings.RCD_DEFAULT_YEAR, role__in=roles
        ).first()
    if membership is None or membership.profile.archived:
        # Otherwise, redirect to the profile list, which includes a "Create new profile" button
        return redirect("rcdprofile:list")

    return redirect("rcdprofile:detail", membership.profile.pk)


def rcd_profile_list(request):
    if not request.user.is_authenticated:
        raise PermissionDenied

    # profiles = request.user.rcd_profiles.filter(archived=False)
    profiles = RCDProfile.objects.filter_can_view(request.user)

    navtree = NavNode(
        "Profiles",
        "",
        current=True,
        children=[
            NavNode(
                str(profile),
                reverse("rcdprofile:detail", kwargs={"pk": profile.pk}),
            )
            for profile in profiles
        ],
    )

    context = {
        "navtree": navtree,
        "current_profiles": profiles.filter(year=settings.RCD_DEFAULT_YEAR),
        "past_profiles": profiles.filter(year__lt=settings.RCD_DEFAULT_YEAR),
    }

    return render(request, "rcdprofile/list.html", context)


def rcd_profile_create(request, institution_pk):
    if not request.user.is_authenticated:
        raise PermissionDenied

    form = RCDProfileForm(request.POST or None)
    institution = request.user.institutions.get(pk=institution_pk)
    form.customize_choices(request, institution)

    if request.method == "POST":
        if form.is_valid():
            profile = RCDProfile.objects.create(
                institution=institution, created_by=request.user, **form.cleaned_data
            )
            messages.success(request, f"Created RCD profile for {profile}")
            send_mail(
                subject=f"RCD Nexus Profile Created for {profile}",
                message=f"A new RCD Profile: {profile} was just created for Institution: {institution}, by creator: {request.user}.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.SUPPORT_EMAIL],
            )
            return redirect("rcdprofile:detail", profile.pk)

    context = {
        "form": form,
        "institution": institution,
        "importable_profiles": request.user.rcd_profiles.filter(archived=False, institution=institution)
        .order_by("-year")
        .filter(),
    }

    return render(request, "rcdprofile/create.html", context)


def rcd_profile_edit(request, pk):
    profile = access_profile(request, pk, "edit")

    form = RCDProfileForm(request.POST or None, instance=profile)
    form.customize_choices(request, profile.institution)

    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, f"Updated RCD profile for {profile}")
            return redirect("rcdprofile:detail", profile.pk)

    context = {
        "form": form,
        "navtree": navtree(profile, re.escape(str(profile))),
        "can_manage": request.user.rcd_profile_memberships.filter(
            profile=profile, role__in=manage_roles
        ).exists(),
    }

    return render(request, "rcdprofile/edit.html", context)


def rcd_profile_import(request):
    if request.method == "POST":
        profile = access_profile(
            request, request.POST.get("imported-profile"), "edit"
        )
        new_profile = RCDProfile.objects.copy(profile, request.user)
        return redirect("rcdprofile:detail", new_profile.pk)

    return redirect("rcdprofile:create")


def rcd_profile_detail(request, pk):
    profile = access_profile(request, pk, "view", allow_archive=True)

    if profile.membership_requests.filter(requested_by=request.user).exists():
        request.user.has_requested_access = True

    context = {
        "profile": profile,
        "navtree": navtree(profile, re.escape(str(profile))),
        "can_edit": request.user.rcd_profile_memberships.filter(
            profile=profile, role__in=edit_roles
        ).exists(),
        "can_manage": request.user.rcd_profile_memberships.filter(
            profile=profile, role__in=manage_roles
        ).exists(),
        "can_submit": request.user.rcd_profile_memberships.filter(
            profile=profile, role=roles.SUBMITTER
        ).exists(),
        "join_note": mark_safe(f"<a href='{reverse('rcdprofile:request-access', kwargs={'pk': pk})}'>Request access</a>"),
    }

    return render(request, "rcdprofile/detail.html", context)


def rcd_profile_archive(request, pk):
    profile = access_profile(request, pk, "submit")

    profile.archived = True
    profile.save(update_fields=["archived"])

    restore_url = reverse("rcdprofile:recovery", kwargs={"pk": profile.pk})
    messages.warning(
        request,
        mark_safe(
            f'Deleted "{profile}". <a href="{restore_url}">Click here to undo.</a>'
        ),
    )
    return redirect("rcdprofile:list")


def rcd_profile_recovery(request, pk):
    if not request.user.is_authenticated:
        raise PermissionDenied

    profile = RCDProfile.objects_archive.get(pk=pk)

    if not request.user.rcd_profile_memberships.filter(
        profile=profile, role=roles.SUBMITTER
    ).exists():
        raise PermissionDenied

    profile.archived = False
    profile.save(update_fields=["archived"])

    messages.success(request, "Profile restored.")
    return redirect("rcdprofile:detail", pk)


def rcd_profile_members(request, pk):
    """
    Profile Managers can edit roles, approve requests, and create invite codes.
    """
    profile = access_profile(request, pk, "manage")

    if request.method == "POST":
        messages.success(request, "Updated member roles.")
        removal_count = 0
        for key, value in request.POST.items():
            if key.startswith("role "):
                _, user_id = key.split()
                if user_id == request.user.pk:
                    messages.error(request, "You cannot change your own role.")
                elif value == "__delete__":
                    removal_count += 1
                    profile.memberships.filter(user_id=user_id).delete()
                else:
                    profile.memberships.filter(user_id=user_id).update(role=value)

        if removal_count:
            messages.warning(request, f"Removed {removal_count} member(s).")


    context = {
        "profile": profile,
        "navtree": navtree(profile, navtree.CONTRIBUTORS),
        "memberships": profile.memberships.all(),
        "role_choices": RCDProfileMember.Role.choices,
        "invite_form": RCDProfileMemberInviteForm(),
    }

    return render(request, "rcdprofile/contributors.html", context)

def rcd_profile_invite(request, pk):
    profile = access_profile(request, pk, "manage")

    if request.method == "POST":
        invite_form = RCDProfileMemberInviteForm(request.POST)
        if invite_form.is_valid():
            email_recipients = invite_form.cleaned_data["email_to"].split()
            invitation = profile.invitations.create(invited_by=request.user)
            invite_link = request.build_absolute_uri(
                reverse("rcdprofile:accept-invite")
            )
            if email_recipients:
                send_mail(
                    subject="RCD Nexus collaboration invite",
                    message=f"{invitation.invited_by} is inviting you to collaborate on RCD Nexus assessments for {profile}.\n\nInvite link: {invite_link}?token={invitation.token}",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=email_recipients,
                )
            messages.success(
                request,
                mark_safe(f"Invite created and sent."
                ),
            )
            return redirect("rcdprofile:members", pk)


def rcd_profile_request_membership(http_request, pk):
    if not RCDProfile.objects.filter_can_view(http_request.user).filter(pk=pk).exists():
        raise PermissionDenied
    RCDProfileMemberRequest.objects.get_or_create(
        profile_id=pk, requested_by=http_request.user
    )
    messages.success(http_request, "Membership request sent. When a profile manager reviews your request, you will be notified by email.")
    return redirect("rcdprofile:list")


def rcd_profile_handle_membership_request(http_request, pk):
    """
    Approves or denies a profile membership request according to the HTTP method (PUT = approve, DELETE = deny).
    """
    profile = access_profile(http_request, pk, "manage")

    if http_request.method == "POST":
        action, user_id = http_request.POST.get("action").split()
        try:
            profile_request: RCDProfileMemberRequest = profile.membership_requests.get(requested_by=user_id)
        except RCDProfileMemberRequest.DoesNotExist:
            pass

        if action == "approve":
            profile_request.approve()
            messages.success(http_request, f"Approved membership request from {profile_request.requested_by}")
            profile_link = http_request.build_absolute_uri(
                reverse("rcdprofile:detail", kwargs={"pk": profile.pk})
            )
            send_mail(
                subject="RCD Nexus membership request approved",
                message=f"Your request to join {profile} has been approved. Link: {profile_link}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[profile_request.requested_by.email],
            )
        elif action == "deny":
            profile_request.deny()
            messages.warning(http_request, f"Denied membership request from {profile_request.requested_by}")
            send_mail(
                subject="RCD Nexus membership request denied",
                message=f"Your request to join {profile} has been denied.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[profile_request.requested_by.email],
            )
            # TODO send email
        else:
            return HttpResponseBadRequest()

    return redirect("rcdprofile:members", pk)


def rcd_profile_invite_accept(request):
    token = request.GET.get("token")

    if not request.user.is_authenticated:
        request.session["profile_invite_token"] = token
        logger.info(dict(request.session.items()))
        raise PermissionDenied(
            mark_safe(
                f"<p>You must first <a href='{reverse('oidc_authentication_init')}'>login to RCD Nexus</a> to accept invites.</p>"
            )
        )

    logger.info(dict(request.session.items()))
    token = token or request.session.get("profile_invite_token")

    if token:
        try:
            invitation: RCDProfileMemberInvite = RCDProfileMemberInvite.objects.filter_valid().get(token=token)
            if "profile_invite_token" in request.session:
                del request.session["profile_invite_token"]
        except RCDProfileMemberInvite.DoesNotExist:
            messages.error(request, "Invalid or expired invitation.")
        else:
            membership, created = invitation.invite(request.user)
            if created:
                messages.success(
                    request, f"You may now contribute to {invitation.profile}!"
                )
            else:
                messages.info(
                    request, f"You are already a member of this RCD Profile, as a {membership.get_role_display()}."
                )
            return redirect("rcdprofile:detail", invitation.profile.pk)

    return render(request, "rcdprofile/invite_accept.html")


# TODO needs work
def rcd_profile_summary(request):
    if not request.user.is_authenticated:
        raise PermissionDenied

    year = settings.RCD_DEFAULT_YEAR

    viewer = request.user.affiliations.all()
    editor = viewer.exclude(role=roles.VIEWER)
    admin = viewer.filter(role=roles.MANAGER)

    institutions = institutions.objects.all()
    editable_orgs = institutions.filter(pk__in=editor.values("institution"))
    admin_orgs = institutions.filter(pk__in=admin.values("institution"))
    my_profiles = (
        RCDProfile.objects.filter(institution__in=viewer.values("institution"))
        .order_by("-year")
        .all()
    )
    active_profiles = my_profiles.filter(year=year)

    navtree = [
        NavNode(
            "Profiles",
            "",
            current=True,
            children=[
                NavNode(
                    str(profile),
                    reverse("rcdprofile:detail", kwargs={"pk": profile.pk}),
                )
                for profile in active_profiles
            ],
        )
    ]

    return render(
        request,
        "rcdprofile/summary.html",
        {
            "editable_orgs": editable_orgs,
            "admin_orgs": admin_orgs,
            "active_profiles": active_profiles,
            "other_profiles": my_profiles.exclude(year=year).order_by("-year")[:10],
            "year": year,
            "navtree": navtree,
        },
    )
