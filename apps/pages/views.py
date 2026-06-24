from django.shortcuts import render, redirect
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages

def about_view(request):
    return render(request, 'pages/about.html')

def contact_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')
        
        full_message = f"Wiadomość od: {name} ({email})\n\n{message}"
        
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

import json
from django.http import JsonResponse
from django.urls import reverse
from apps.trainers.models import TrainerProfile
from apps.accounts.models import TrainerStatus
from .services import get_ai_sport_recommendation, AIServiceError

def quiz_submit_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            answers = data.get('answers', [])
            
            if not answers:
                return JsonResponse({'error': 'Brak odpowiedzi'}, status=400)
                
            from apps.trainers.models import Sport
            available_sports = list(Sport.objects.filter(trainers__in=approved_trainers).values_list('name', flat=True).distinct())
            
            try:
                ai_result = get_ai_sport_recommendation(answers, available_sports)
            except AIServiceError as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error("AI Service Error: %s", str(e), exc_info=True)
                return JsonResponse({'error': str(e)}, status=500)
            
            suggested_sport = ai_result.get('suggested_sport', '')
            
            # Find recommended trainers
            recommended_trainers = []
            if suggested_sport:
                matched_trainers = approved_trainers.filter(sports__name__icontains=suggested_sport).distinct()[:3]
                for t in matched_trainers:
                    recommended_trainers.append({
                        'name': t.full_name,
                        'sport': ", ".join([s.name for s in t.sports.all()]),
                        'url': reverse('trainers:public_profile', kwargs={'username': t.username}),
                        'location': t.location,
                        'type': t.get_training_type_display()
                    })
            
            return JsonResponse({
                'recommendation': ai_result.get('recommendation', ''),
                'suggested_sport': suggested_sport,
                'trainers': recommended_trainers
            })
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error("Unexpected error in quiz_submit_api: %s", str(e), exc_info=True)
            return JsonResponse({'error': 'Wystąpił nieoczekiwany błąd serwera.'}, status=500)
            
    return JsonResponse({'error': 'Metoda nieobsługiwana'}, status=405)

from django.core.paginator import Paginator
from apps.trainers.models import TrainerPost

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

