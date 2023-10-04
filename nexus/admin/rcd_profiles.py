from typing import Any
from nexus.models import (
    RCDProfile,
    RCDProfileMember,
    Facing,
    FacingContent,
)

from django.contrib import admin

class FacingContentInline(admin.StackedInline):
    model = FacingContent
    extra = 0

@admin.register(Facing)
class FacingAdmin(admin.ModelAdmin):
    inlines = [FacingContentInline]

class RCDProfileMemberInline(admin.TabularInline):
    model = RCDProfileMember
    autocomplete_fields = ["user"]
    extra = 0

@admin.register(RCDProfile)
class RCDProfileAdmin(admin.ModelAdmin):
    list_display = ["__str__", "created_by"]
    list_filter = ["archived"]
    search_fields = ["institution__name", "institution_subunit"]
    inlines = [RCDProfileMemberInline]
