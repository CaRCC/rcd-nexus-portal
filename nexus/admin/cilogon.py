from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from nexus.models import FederatedIdentity, IdentityProvider, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    pass


admin.site.register(IdentityProvider)
admin.site.register(FederatedIdentity)
