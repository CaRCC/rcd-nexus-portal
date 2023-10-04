from django.contrib import admin

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
        "student_pop",
        "grad_pop",
        "undergrad_pop",
        "research_expenditure",
    ]
    search_fields = ["name"]
    list_filter = [
        "carnegie_classification",
        "ipeds_region",
        "ipeds_sector",
        "ipeds_control",
        "ipeds_size",
        "ipeds_tcu",
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
                    "ipeds_hbcu",
                    "ipeds_tcu",
                    "ipeds_urbanization",
                    "ipeds_land_grant",
                    "carnegie_classification",
                )
            },
        ),
    )


@admin.register(NewInstitutionRequest)
class NewInstitutionRequestAdmin(admin.ModelAdmin):
    list_display = ["name", "internet_domain", "requester", "created", "comment"]
    actions = ["approve"]

    def approve(self, request, queryset):
        for req in queryset:
            institution = req.approve()
            self.message_user(
                request,
                f"Approved new institution request for '{institution}'",
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