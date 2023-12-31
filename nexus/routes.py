"""RCD Nexus URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path

from nexus.views.rcd_profiles import index

admin.site.site_header = "RCD Nexus administration"
admin.site.site_title = "RCD Nexus admin"

urlpatterns = [
    path("", index, name="index"),
    path("admin/", admin.site.urls),
    path("oidc/", include("mozilla_django_oidc.urls")),
    path("profiles/", include("nexus.urls.rcd_profiles")),
    path("capmodel-assessment/", include("nexus.urls.capmodel")),
    path("institutions/", include("nexus.urls.institutions")),
    path("accounts/profile/", lambda request: redirect("index")),
    path("helpdocs/", include("nexus.urls.helpdocs")),
]
