from django.contrib import admin
from nexus.models import MOTD
from django.db import models
from django.forms import Textarea

@admin.register(MOTD)
class MOTDAdmin(admin.ModelAdmin):
    list_display = ["message"]
    formfield_overrides = {
        models.CharField: {"widget": Textarea},
    }
