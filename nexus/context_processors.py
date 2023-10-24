from nexus.models import MOTD 

def base_template(request):
    template = "base.html"
    if request.htmx:
        template = "base_htmx.html"
        #if request.modal:
        #    template = "base_modal.html"

    return {"base_template": template}

def motd_message(request):
    message = MOTD.getMOTD()
    return {"motd": message}
