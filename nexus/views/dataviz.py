from django.urls import reverse
from django.conf import settings
from django.http import HttpRequest
from django.shortcuts import redirect, render


def data_viz_main(request): 
    return render(request, "dataviz/vizmain.html", {})

