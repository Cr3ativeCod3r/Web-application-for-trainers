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
import os
import google.generativeai as genai
from django.http import JsonResponse

from apps.trainers.models import TrainerProfile
from apps.accounts.models import TrainerStatus

def quiz_submit_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            answers = data.get('answers', [])
            
            if not answers:
                return JsonResponse({'error': 'Brak odpowiedzi'}, status=400)
                
            # Query all active trainers to find available sports
            approved_trainers = TrainerProfile.objects.filter(user__status=TrainerStatus.APPROVED_TRAINER)
            available_sports = set()
            for trainer in approved_trainers:
                available_sports.update(trainer.sports_list)
            
            sports_str = ", ".join(sorted(list(available_sports))) if available_sports else "Brak sportów w bazie"
            
            prompt = f"""Na podstawie poniższych odpowiedzi użytkownika na 13 pytań, doradź mu jaki sport będzie dla niego najlepszy.
Z poniższej listy sportów (to dyscypliny oferowane przez naszych trenerów), wybierz JEDEN, który najlepiej pasuje: [{sports_str}]. 
Jeśli żaden nie pasuje w 100%, wybierz ten najbliższy prawdy. 

Zwróć odpowiedź WYŁĄCZNIE jako poprawny obiekt JSON (bez markdown block) o strukturze:
{{
  "text": "Twój motywujący tekst (2-3 akapity). Pisz jako profesjonalny trener.",
  "suggested_sport": "Dokładna nazwa wybranego sportu z listy"
}}

Odpowiedzi użytkownika:
"""
            for item in answers:
                prompt += f"Pytanie: {item.get('question')}\nOdpowiedź: {item.get('answer')}\n\n"
                
            api_key = os.environ.get('API_GEMINI') or os.environ.get('api_gemini')
            if not api_key:
                return JsonResponse({'error': 'Brak klucza API Gemini w konfiguracji serwera.'}, status=500)
                
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-3.5-flash')
            response = model.generate_content(prompt)
            
            # Parse JSON
            try:
                response_text = response.text.strip()
                if response_text.startswith('```json'):
                    response_text = response_text[7:-3].strip()
                elif response_text.startswith('```'):
                    response_text = response_text[3:-3].strip()
                
                result_data = json.loads(response_text)
                ai_text = result_data.get('text', 'Błąd w formacie tekstu.')
                suggested_sport = result_data.get('suggested_sport', '')
            except Exception as e:
                return JsonResponse({'error': 'Model zwrócił nieprawidłowy format (oczekiwano JSON). ' + str(e)}, status=500)
            
            # Find recommended trainers
            recommended_trainers = []
            if suggested_sport:
                matched_trainers = approved_trainers.filter(sport__icontains=suggested_sport)[:3]
                for t in matched_trainers:
                    from django.urls import reverse
                    recommended_trainers.append({
                        'name': t.full_name,
                        'sport': t.sport,
                        'url': reverse('trainers:public_profile', kwargs={'username': t.username}),
                        'location': t.location,
                        'type': t.get_training_type_display()
                    })
            
            return JsonResponse({
                'recommendation': ai_text,
                'suggested_sport': suggested_sport,
                'trainers': recommended_trainers
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
            
    return JsonResponse({'error': 'Metoda nieobsługiwana'}, status=405)
