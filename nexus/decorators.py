def htmx_fragment(view_function):
    def inner(request, *args, **kwargs):
        response = view_function(request, *args, **kwargs)
        response.