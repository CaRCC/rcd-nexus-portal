from django.utils.html import escape
from django.utils.safestring import mark_safe


def compute_answer_color(value: float):
    if value is None:
        return 0;

    value = min(1.0, max(0.0, value))
    if value < 0.2 :
        rgbcolor = "var(--heatmap-quint-1)"
    elif  value < 0.4 :
        rgbcolor = "var(--heatmap-quint-2)"
    elif  value < 0.6 :
        rgbcolor = "var(--heatmap-quint-3)"
    elif  value < 0.8 :
        rgbcolor = "var(--heatmap-quint-4)"
    else :
        rgbcolor = "var(--heatmap-quint-5)"
    return rgbcolor

def html_highlight(string, value: float):
    if value is None:
        return string

    rgbcolor = compute_answer_color(value)
    return mark_safe(
        f"<span style='background-color:{rgbcolor}'>{escape(string)}</span>"
    )
