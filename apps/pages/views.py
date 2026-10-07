import json
import logging

from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from apps.accounts.models import TrainerStatus
from apps.trainers.models import Sport, TrainerPost, TrainerProfile

from .services import AIServiceError, get_ai_sport_recommendation

logger = logging.getLogger(__name__)

def about_view(request):
    return render(request, 'pages/about.html')

def contact_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')

        context = {'name': name, 'email': email, 'message': message}
        full_message = render_to_string('pages/emails/contact_form.txt', context)

        send_mail(
            subject=f"Nowa wiadomość z formularza kontaktowego Coachly od {name}",
            message=full_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.DEFAULT_FROM_EMAIL],
            fail_silently=False,
        )

        messages.success(request, "Twoja wiadomość została wysłana. Dziękujemy za kontakt!")
        return redirect('pages:contact')

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

