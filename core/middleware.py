from django.http import JsonResponse
from django.shortcuts import render
from django_ratelimit.exceptions import Ratelimited


class RatelimitMiddleware:
    """
    Middleware that catches Ratelimited exceptions raised by django-ratelimit
    and returns a 429 Too Many Requests response: a friendly page for browsers,
    JSON for API/fetch calls (so frontend code can parse it).
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if not isinstance(exception, Ratelimited):
            return None
        if request.content_type == 'application/json' or 'application/json' in request.headers.get('Accept', ''):
            return JsonResponse({'error': 'Zbyt wiele żądań. Spróbuj ponownie za chwilę.'}, status=429)
        return render(request, 'ratelimited.html', status=429)
