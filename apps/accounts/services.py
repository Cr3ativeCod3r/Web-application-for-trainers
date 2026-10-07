from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode

from .models import ClientProfile
from .tasks import send_activation_email_client_task, send_activation_email_task

User = get_user_model()

class AuthService:
    @staticmethod
    def _create_inactive_user(email, password):
        # The manager hashes the password; the account stays inactive until e-mail activation.
        return User.objects.create_user(email=email, password=password, is_active=False)

    @staticmethod
    @transaction.atomic
    def register_trainer(email, password, domain):
        """
        Creates an inactive trainer account and sends the activation e-mail asynchronously.
        """
        user = AuthService._create_inactive_user(email, password)
        # Queue the e-mail only after COMMIT: otherwise the worker may run before the row
        # is visible (User.DoesNotExist) or send a link for a user that was rolled back.
        transaction.on_commit(lambda: send_activation_email_task.delay(user.pk, domain))
        return user

    @staticmethod
    @transaction.atomic
    def register_client(email, password, domain, first_name, last_name):
        """
        Creates an inactive client account together with its profile (all-or-nothing)
        and sends the client activation e-mail asynchronously.
        """
        user = AuthService._create_inactive_user(email, password)
        ClientProfile.objects.create(user=user, first_name=first_name, last_name=last_name)
        transaction.on_commit(lambda: send_activation_email_client_task.delay(user.pk, domain))
        return user

    @staticmethod
    def activate_account(uidb64, token):
        """
        Validates the token and activates the user account.
        Returns (True, user) on success, or (False, None) on failure.
        """
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            user.is_active = True
            user.save(update_fields=['is_active'])
            return True, user

        return False, None
