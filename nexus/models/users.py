from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    def __str__(self):
        if not self.first_name:
            return self.username
    
        return f"{self.first_name} {self.last_name} ({self.username})"
