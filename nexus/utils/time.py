from datetime import timedelta

from django.utils import timezone


def current_year():
    return timezone.now().year


def next_week():
    return timezone.now() + timedelta(days=7)
