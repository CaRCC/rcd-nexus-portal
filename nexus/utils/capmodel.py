from django.utils.html import escape
from django.utils.safestring import mark_safe


def compute_answer_color(value: float):
    if value is None:
        return 0;

    value = min(1.0, max(0.0, value))
    if value < 0.2 :
        rgbcolor = "#f4cccc"
    elif  value < 0.4 :
        rgbcolor = "#fce5cd"
    elif  value < 0.6 :
        rgbcolor = "#fff2cc"
    elif  value < 0.8 :
        rgbcolor = "#d7eec5"
    else :
        rgbcolor = "#b6d7a8"
    return rgbcolor

def html_highlight(string, value: float):
    if value is None:
        return string

    rgbcolor = compute_answer_color(value)
    return mark_safe(
        f"<span style='background-color:{rgbcolor}'>{escape(string)}</span>"
    )
