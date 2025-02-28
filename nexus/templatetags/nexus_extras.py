from django import template
from django.utils.safestring import mark_safe
import re

register = template.Library()

@register.simple_tag
def get_verbose_name(object, fieldnm): 
  return object._meta.get_field(fieldnm).verbose_name

@register.simple_tag
def setvar(val=None):
    return val

@register.filter
def nps_br(str):
    return mark_safe(re.sub(r'^(\d+)', r'\1<br>', str))