from django.urls import reverse
from django.conf import settings
from django.contrib import messages
from django.http import HttpRequest
from django.shortcuts import redirect, render


def help_docs_home(request):
    return render(request, "helpdocs/main.html", {})

def help_faq(request):
    context = {}

    return render(request, "helpdocs/faq.html", context)

def help_intro_and_guide(request):
    context = {}

    return render(request, "helpdocs/intro_and_guide.html", context)

def help_quickstart(request):
    context = {}

    return render(request, "helpdocs/quickstart.html", context)

def printable_questions(request):
    context = {}

    return render(request, "helpdocs/printable_questions.html", context)

