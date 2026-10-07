from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string


@shared_task(autoretry_for=(OSError,), retry_backoff=True, max_retries=3)
def send_contact_email_task(name: str, email: str, message: str) -> None:
    body = render_to_string('pages/emails/contact_form.txt', {'name': name, 'email': email, 'message': message})
    EmailMessage(
        subject=f"Nowa wiadomość z formularza kontaktowego Coachly od {name}",
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[settings.DEFAULT_FROM_EMAIL],
        # "Reply" in the mail client answers the person who wrote, not ourselves.
        reply_to=[email],
    ).send(fail_silently=False)
