from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth import get_user_model

User = get_user_model()

@shared_task
def send_activation_email_task(user_id, domain):
    """Activation email for trainers."""
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return "User not found"

    subject = 'Aktywuj swoje konto trenera – Coachly'

    context = {
        'user': user,
        'domain': domain,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': default_token_generator.make_token(user),
    }

    message = render_to_string('emails/trainers/activation.txt', context)
    html_message = render_to_string('emails/trainers/activation.html', context)

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=html_message,
        fail_silently=False,
    )
    return "Trainer activation email sent"


@shared_task
def send_activation_email_client_task(user_id, domain):
    """Activation email for regular clients."""
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return "User not found"

    subject = 'Aktywuj swoje konto – Coachly'

    context = {
        'user': user,
        'domain': domain,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': default_token_generator.make_token(user),
    }

    message = render_to_string('emails/clients/activation.txt', context)
    html_message = render_to_string('emails/clients/activation.html', context)

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=html_message,
        fail_silently=False,
    )
    return "Client activation email sent"
