from django.contrib.auth.models import AbstractUser
from django.db import models

# Provides a simple means of broadcasting a message to all users, through the admin UI
# Designed to behave like a singleton, where the admin UI is the only means to set the message. 
class MOTD(models.Model):
    message = models.CharField(
        max_length=255,
        blank=True,
    )
    @classmethod
    def getMOTD(cls) :
        try:
            motd = cls.objects.get()
            return motd.message
        except cls.DoesNotExist:
            return ""
        