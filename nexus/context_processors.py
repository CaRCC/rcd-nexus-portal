from nexus.models import MOTD 
from django.conf import settings

def base_template(request):
    template = "base.html"
    #if request.htmx:
        #template = "base_htmx.html"
        #if request.modal:
        #    template = "base_modal.html"

    return {
        "base_template": template,
        "cc_license_url" : settings.CC_LICENSE_URL,
        "cc_license_string" : settings.CC_LICENSE_STRING,
        "cc_license_desc" : settings.CC_LICENSE_DESC,
        }

def motd_message(request):
    message, dismissDays = MOTD.getMOTD()
    return {"motd": message, "dismissDays": dismissDays}
