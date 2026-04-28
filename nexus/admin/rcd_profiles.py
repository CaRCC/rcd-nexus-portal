from typing import Any
from nexus.models import (
    RCDProfile,
    RCDProfileMember,
    Facing,
    FacingContent,
    PostCompletionSurvey,
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
    list_display = ["__str__", "year", "created_by"]
    list_filter = ["archived", "year", "mission", "org_chart"]
    search_fields = ["institution__name", "institution_subunit"]
    inlines = [RCDProfileMemberInline]

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        if search_term:
            # This applies unaccent to the search
            queryset = self.model.objects.filter(institution__name__unaccent__icontains=search_term)
        return queryset, use_distinct

@admin.register(PostCompletionSurvey)
class PostCompletionSurveyAdmin(admin.ModelAdmin):
    list_display = ["profile"]
