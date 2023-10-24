from django.contrib import admin
from nexus.models import MOTD

@admin.register(MOTD)
class MOTDAdmin(admin.ModelAdmin):
    list_display = ["message"]
