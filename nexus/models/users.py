from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    def __str__(self):
        if not self.first_name:
            return self.username
    
        return f"{self.first_name} {self.last_name} ({self.username})"

    def name(self):
        if not self.first_name:
            return ""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def is_capmodel_contributor(self):
        for profile in self.rcd_profiles.filter(year__gte=timezone.now()-timezone.timedelta(days=365*3)):
            if profile.capabilities_assessment.review_status == "approved":
                return True
        return False