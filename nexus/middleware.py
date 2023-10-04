def allow_cors(get_response):
    def middleware(request):
        response = get_response(request)
        response["Access-Control-Allow-Origin"] = "*"
        return response
    return middleware

def htmx(get_response):
    def middleware(request):
        request.htmx = ("HX-Request" in request.headers)
        return get_response(request)
    return middleware