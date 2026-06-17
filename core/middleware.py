from django.shortcuts import render
from django_ratelimit.exceptions import Ratelimited

class RatelimitMiddleware:
    """
    Middleware that catches Ratelimited exceptions raised by django-ratelimit
    and returns a user-friendly 429 Too Many Requests page.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if isinstance(exception, Ratelimited):
            return render(request, 'ratelimited.html', status=429)
        return None
