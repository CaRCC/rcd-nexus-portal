from django.contrib import admin
from django.db.models import Q

from nexus.models import Institution, InstitutionAffiliation, NewInstitutionRequest, AffiliationRequest


class InstitutionAffiliationInline(admin.TabularInline):
    model = InstitutionAffiliation
    extra = 0
    verbose_name = "affiliated user"


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ["name", "country", "state_or_province", "internet_domain"]
    readonly_fields = [
        "has_cilogon_idp",
    ]
    search_fields = ['name', 'internet_domain', 'country']
    list_filter = [
        # allow filtering by the carnegie_classification values, and by null
        "carnegie_classification",
        "ipeds_control",
        "ipeds_region",
        "ipeds_epscor",
        "ipeds_size",
        #"ipeds_sector",
        "ipeds_msi",
        "ipeds_hbcu",
        "ipeds_pbi",
        "ipeds_tcu",
        "ipeds_hsi",
        "ipeds_aanapisi_annh",
    ]
    inlines = [InstitutionAffiliationInline]
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "country",
                    "state_or_province",
                    "internet_domain",
                    "has_cilogon_idp",
                    "list_as_contributor",
                )
            },
        ),
        (
            "Metrics",
            {
                "fields": (
                    "student_pop",
                    "grad_pop",
                    "undergrad_pop",
                    "research_expenditure",
                )
            },
        ),
        (
            "IPEDS",
            {
                "fields": (
                    "ipeds_region",
                    "ipeds_sector",
                    "ipeds_level",
                    "ipeds_control",
                    "ipeds_epscor",
                    "ipeds_size",
                    "ipeds_hbcu",
                    "ipeds_pbi",
                    "ipeds_tcu",
                    "ipeds_hsi",
                    "ipeds_aanapisi_annh",
                    "ipeds_msi",
                    "ipeds_urbanization",
                    "ipeds_land_grant",
                    "carnegie_classification",
                )
            },
        ),
    )
    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        if search_term:
            # This applies unaccent to the search
            queryset |= self.model.objects.filter(
                            Q(name__unaccent__icontains=search_term) |
                            Q(internet_domain__icontains=search_term) |
                            Q(country__icontains=search_term) )
        return queryset, use_distinct

@admin.register(NewInstitutionRequest)
class NewInstitutionRequestAdmin(admin.ModelAdmin):
    list_display = ["name", "internet_domain", "requester", "created", "comment"]
    actions = ["approve", "reject_dupe"]

    def approve(self, request, queryset):
        for req in queryset:
            institution = req.approve(request)
            self.message_user(
                request,
                f"Approved new institution request for '{institution}'",
                level="success",
            )

    @admin.action(description="Reject selected Institutions requests as duplicates")
    def reject_dupe(self, request, queryset):
        for req in queryset:
            institution = req.reject_dupe(request)
            self.message_user(
                request,
                f"Rejected new institution request for '{institution}' as a duplicate",
                level="success",
            )

@admin.register(AffiliationRequest)
class AffiliationRequestAdmin(admin.ModelAdmin):
    list_display = ["user", "institution", "email", "expires"]
    actions = ["approve"]
    readonly_fields = ["user", "institution", "email", "token"]

    def approve(self, request, queryset):
        for req in queryset:
            req.approve()
            self.message_user(
                request,
                f"Approved affiliation request for '{req.user}'",
                level="success",
            )