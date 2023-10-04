from django.urls import path

from nexus.views.rcd_profiles import *

app_name = "rcdprofile"

urlpatterns = [
    path("", rcd_profile_list, name="list"),
    path("create/<int:institution_pk>", rcd_profile_create, name="create"),
    path("import", rcd_profile_import, name="import"),
    path("<int:pk>/", rcd_profile_detail, name="detail"),
    path("<int:pk>/edit", rcd_profile_edit, name="edit"),
    path("<int:pk>/members/", rcd_profile_members, name="members"),
    path("<int:pk>/members/invite", rcd_profile_invite, name="invite"),
    path("<int:pk>/members/request", rcd_profile_request_membership, name="request-access"),
    path("<int:pk>/members/handle-requests", rcd_profile_handle_membership_request, name="handle-access-request"),
    path("<int:pk>/archive", rcd_profile_archive, name="archive"),
    path("<int:pk>/recover", rcd_profile_recovery, name="recovery"),
    path("invite", rcd_profile_invite_accept, name="accept-invite"),
    # path("explore", explore_data, name="explore"),
]
