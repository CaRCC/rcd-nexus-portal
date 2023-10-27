"""
Local development settings. Do not put anything sensitive in here, and do not use or import for production!
"""

from nexus.settings import *
import os

DEBUG = True
ALLOWED_HOSTS = ["localhost"]

ADMINS = [("Paul Fischer", "p.fischer@utah.edu")]
SERVER_EMAIL = "errors@portal.rcd-nexus.org"

SECRET_KEY = "django-insecure-d=j15d$97td$27$3xwx!wz0^%!#d3#_l7h_*mr043p47wn5@7d"

BASE_URL = "http://localhost:8000"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "django",
        "USER": "django",
        "PASSWORD": "django",
        "HOST": "localhost",
    }
}

from django.utils.log import DEFAULT_LOGGING
LOGGING = DEFAULT_LOGGING
LOGGING["handlers"]["console"]["filters"].remove("require_debug_true")



OIDC_RP_CLIENT_ID = os.environ.get("CILOGON_CLIENT_ID")
OIDC_RP_CLIENT_SECRET = os.environ.get("CILOGON_CLIENT_SECRET")


# Send emails to stdout rather than sending them for real
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
