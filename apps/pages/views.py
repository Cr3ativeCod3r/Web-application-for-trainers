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

def quiz_submit_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            answers = data.get('answers', [])
            
            if not answers:
                return JsonResponse({'error': 'Brak odpowiedzi'}, status=400)
                
            prompt = "Na podstawie poniższych odpowiedzi użytkownika na 13 pytań, doradź mu jaki sport będzie dla niego najlepszy. Podaj konkretne 1-2 propozycje oraz krótkie, motywujące uzasadnienie. Pisz jako profesjonalny trener.\n\n"
            for item in answers:
                prompt += f"Pytanie: {item.get('question')}\nOdpowiedź: {item.get('answer')}\n\n"
                
            api_key = os.environ.get('API_GEMINI') or os.environ.get('api_gemini')
            if not api_key:
                return JsonResponse({'error': 'Brak klucza API Gemini w konfiguracji serwera.'}, status=500)
                
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-3.5-flash')
            response = model.generate_content(prompt)
            
            return JsonResponse({'recommendation': response.text})
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
            
    return JsonResponse({'error': 'Metoda nieobsługiwana'}, status=405)
