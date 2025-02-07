from django.conf import settings
from django.contrib import admin
from django.core.mail import send_mail
from django.utils import timezone

from nexus.models import (
    CapabilitiesAnswer,
    CapabilitiesAssessment,
    CapabilitiesQuestion,
    CapabilitiesQuestionContent,
    CapabilitiesTopic,
    CapabilitiesTopicContent
)

class TopicContentInline(admin.StackedInline):
    model = CapabilitiesTopicContent
    extra = 0

class QuestionContentInline(admin.StackedInline):
    model = CapabilitiesQuestionContent
    extra = 0


class AnswerInline(admin.TabularInline):
    model = CapabilitiesAnswer
    extra = 0


@admin.register(CapabilitiesTopic)
class TopicAdmin(admin.ModelAdmin):
    inlines = [TopicContentInline]

@admin.register(CapabilitiesQuestion)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ["legacy_qid", "fully_qualified_slug", "get_shorttext", "is_essential"]
    list_filter = ["is_essential"]
    inlines = [QuestionContentInline]
    ordering = ["topic__facing__index", "topic__index", "index"]
    
    def get_shorttext(self, obj):
        return obj.contents.get(language="en").shorttext



@admin.register(CapabilitiesAssessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ["profile", "assessment_type", "completed_percent", "review_status", "review_note", "review_time"]
    list_filter = ["review_status", "assessment_type", "profile__year"]
    search_fields = ["review_note", "profile__institution__name"]
    readonly_fields = ["profile"]
#    inlines = [AnswerInline]
    actions = ["approve"]

    def approve(self, request, queryset):
#        queryset.update(
#            review_status=CapabilitiesAssessment.ReviewStatusChoices.APPROVED,
#            review_user=request.user,
#            review_time=timezone.now(),
#        )
        for assmnt in queryset:
            submitter = assmnt.update_user
            profile = assmnt.profile
            assmnt.review_status=CapabilitiesAssessment.ReviewStatusChoices.APPROVED
            assmnt.review_user=request.user
            assmnt.review_time=timezone.now()
            assmnt.save()
            if(submitter):
                send_mail(
                    subject=f"RCD Nexus Capabilities Model Assessment Approved",
                    message=f"""Your recently submitted assessment for Profile: {profile} has been approved.

Your assessment data will be added to the community dataset, benefitting the entire community.

On behalf of the CaRCC Capabilities Model working group - Thanks!
""",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[submitter.email],
                )
