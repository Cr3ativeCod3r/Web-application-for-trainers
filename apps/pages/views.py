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
