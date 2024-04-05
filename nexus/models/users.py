import datetime
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from nexus.models.capmodel import CapabilitiesAssessment


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
        currYear = datetime.date.today().year
        # After 2024, only contributors in the past three years have privileges
        cutoffyear = currYear-3
        # print(f'Minimum year for contributors is: {cutoffyear}')
        for profile in self.rcd_profiles.filter(capabilities_assessment__review_status=CapabilitiesAssessment.ReviewStatusChoices.APPROVED):
            # All contributors are good until the end of 2024, so if there are any approved ones they're good
            if currYear == 2024 or profile.year >= cutoffyear:
                return True
        return False