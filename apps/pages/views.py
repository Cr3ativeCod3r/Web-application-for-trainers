import json
import logging

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from apps.accounts.models import TrainerStatus
from apps.trainers.models import Sport, TrainerPost, TrainerProfile

from .forms import ContactForm
from .services import AIServiceError, get_ai_sport_recommendation
from .tasks import send_contact_email_task

logger = logging.getLogger(__name__)

def about_view(request):
    return render(request, 'pages/about.html')

@ratelimit(key='ip', rate='3/h', method='POST', block=True)
def contact_view(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # Sent by Celery: a slow or failing SMTP server must not block or crash the request.
            send_contact_email_task.delay(**form.cleaned_data)
            messages.success(request, "Twoja wiadomość została wysłana. Dziękujemy za kontakt!")
            return redirect('pages:contact')
        for errors in form.errors.values():
            messages.error(request, errors[0])

    return render(request, 'pages/contact.html')


def privacy_view(request):
    return render(request, 'pages/privacy.html')

def quiz_view(request):
    return render(request, 'pages/quiz.html')

MAX_QUIZ_ANSWERS = 20
MAX_QUIZ_TEXT_LENGTH = 500


def _clean_quiz_answers(raw_answers) -> list[dict] | None:
    """Validates the client payload; every character ends up in a paid LLM prompt."""
    if not isinstance(raw_answers, list) or not 0 < len(raw_answers) <= MAX_QUIZ_ANSWERS:
        return None
    answers = []
    for item in raw_answers:
        if not isinstance(item, dict):
            return None
        answers.append({
            'question': str(item.get('question', ''))[:MAX_QUIZ_TEXT_LENGTH],
            'answer': str(item.get('answer', ''))[:MAX_QUIZ_TEXT_LENGTH],
        })
    return answers


@transaction.non_atomic_requests  # do not hold a DB transaction open while waiting for Gemini
@require_POST
@ratelimit(key='ip', rate='5/h', block=True)
def quiz_submit_api(request):
    try:
        payload = json.loads(request.body)
    except ValueError:
        return JsonResponse({'error': 'Nieprawidłowe dane.'}, status=400)

    answers = _clean_quiz_answers(payload.get('answers') if isinstance(payload, dict) else None)
    if answers is None:
        return JsonResponse({'error': 'Brak odpowiedzi lub nieprawidłowy format.'}, status=400)

    approved_trainers = TrainerProfile.objects.filter(user__status=TrainerStatus.APPROVED_TRAINER)
    available_sports = list(Sport.objects.filter(trainers__in=approved_trainers).values_list('name', flat=True).distinct())

    try:
        ai_result = get_ai_sport_recommendation(answers, available_sports)
    except AIServiceError:
        # Details (API errors, quota info) go to the logs, not to the browser.
        logger.exception("AI sport recommendation failed")
        return JsonResponse({'error': 'Nie udało się teraz przygotować rekomendacji. Spróbuj ponownie później.'}, status=502)

    suggested_sport = ai_result.get('suggested_sport', '')

    recommended_trainers = []
    if suggested_sport:
        matched_trainers = (
            approved_trainers.filter(sports__name__icontains=suggested_sport)
            .prefetch_related('sports')
            .distinct()[:3]
        )
        for t in matched_trainers:
            recommended_trainers.append({
                'name': t.full_name,
                'sport': ", ".join(s.name for s in t.sports.all()),
                'url': reverse('trainers:public_profile', kwargs={'username': t.username}),
                'location': t.location,
                'type': t.get_training_type_display()
            })

    return JsonResponse({
        'recommendation': ai_result.get('recommendation', ''),
        'suggested_sport': suggested_sport,
        'trainers': recommended_trainers
    })


def knowledge_base_view(request):
    query = request.GET.get('q', '').strip()

    # Get all posts from approved trainers
    posts = TrainerPost.objects.filter(trainer__user__status=TrainerStatus.APPROVED_TRAINER).order_by('-created_at')

    if query:
        posts = posts.filter(title__icontains=query)

    paginator = Paginator(posts, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'pages/knowledge_base.html', {
        'posts': page_obj,
        'query': query
    })

