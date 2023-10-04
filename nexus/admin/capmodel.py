from django.contrib import admin
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
    inlines = [QuestionContentInline]


@admin.register(CapabilitiesAssessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ["profile", "review_status", "review_note", "review_time"]
    readonly_fields = ["profile"]
    inlines = [AnswerInline]
    actions = ["approve"]

    def approve(self, request, queryset):
        queryset.update(
            review_status=CapabilitiesAssessment.ReviewStatusChoices.APPROVED,
            review_user=request.user,
            review_time=timezone.now(),
        )
