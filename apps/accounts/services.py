from django.contrib.auth import get_user_model
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.tokens import default_token_generator
from .tasks import send_activation_email_task, send_activation_email_client_task

User = get_user_model()

class AuthService:    
    @staticmethod
    def register_trainer(email, password, domain):
        """
        Creates a new user with an 'inactive' status and dispatches an activation email asynchronously.
        """
        # Utilize the manager, which automatically hashes the password during creation
        user = User.objects.create_user(email=email, password=password)
        user.is_active = False
        user.save()
        
        # Dispatch email sending in the background (Celery)
        send_activation_email_task.delay(user.pk, domain)
        return user

    @staticmethod
    def register_client(email, password, domain):
        """
        Creates a new user with an 'inactive' status and dispatches a client activation email asynchronously.
        """
        user = User.objects.create_user(email=email, password=password)
        user.is_active = False
        user.save()

        # Dispatch email sending in the background (Celery)
        send_activation_email_client_task.delay(user.pk, domain)
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
            user.save()
            return True, user
        
        return False, None
