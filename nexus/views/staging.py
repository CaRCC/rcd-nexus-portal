"""Controls for staging environment"""
from django.http import HttpResponseForbidden, HttpResponseBadRequest
from django.contrib import messages
from django.shortcuts import redirect
import subprocess
import shlex


def staging_command(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden()
    
    form_action = request.POST.get('form-action')

    if not form_action:
        return HttpResponseBadRequest("missing form-action")
    
    try:
        command = ['./staging-controls.sh', shlex.quote(form_action)]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        messages.success(request, f"Command '{command}' executed successfully!")
        print("Output:", result.stdout)
        print("Error:", result.stderr)
    except subprocess.CalledProcessError as e:
        messages.error(request, f"Command '{command}' failed with return code {e.returncode}.")

    if stdout := result.stdout:
        messages.info(request, stdout)

    if stderr := result.stderr:
        messages.warning(request, stderr)

    return redirect('admin:index')
