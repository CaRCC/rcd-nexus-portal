from django.contrib.auth.models import AbstractUser
from django.db import models

# Provides a simple means of broadcasting a message to all users, through the admin UI
# Designed to behave like a singleton, where the admin UI is the only means to set the message. 
class MOTD(models.Model):
    message = models.CharField(
        max_length=255,
        blank=True,
    )
    # Days to pause the message if the user dismisses it (e.g., using a cookie timeout)
    timeout = models.PositiveIntegerField(
        "Cookie timeout",
        default=1, 
    )

    @classmethod
    def getMOTD(cls) :
        try:
            motd = cls.objects.get()
            return motd.message, motd.timeout
        except cls.DoesNotExist:
            return "", 0
        