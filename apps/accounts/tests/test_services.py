import pytest
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator

from apps.accounts.services import AuthService
from apps.accounts.tasks import send_activation_email_task
from apps.accounts.tests.factories import UserFactory

User = get_user_model()

@pytest.mark.django_db
class TestAuthService:
    @patch('apps.accounts.services.send_activation_email_task.delay')
    def test_register_trainer_creates_inactive_user_and_sends_email(self, mock_send_email_task):
        """Test that registering a trainer creates a user, sets active=False, and delays the task."""
        email = "trainer@example.com"
        password = "trainerpass123"
        domain = "testserver.com"
        
        user = AuthService.register_trainer(email=email, password=password, domain=domain)
        
        assert user.email == email
        assert user.is_active is False
        mock_send_email_task.assert_called_once_with(user.pk, domain)

    def test_activate_account_successful(self):
        """Test account activation with a valid token and uidb64."""
        user = UserFactory(is_active=False)
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        success, activated_user = AuthService.activate_account(uidb64, token)

        assert success is True
        assert activated_user.pk == user.pk
        
        # Refresh from DB
        user.refresh_from_db()
        assert user.is_active is True

    def test_activate_account_invalid_token(self):
        """Test account activation fails with an invalid token."""
        user = UserFactory(is_active=False)
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        invalid_token = "invalid-token"

        success, activated_user = AuthService.activate_account(uidb64, invalid_token)

        assert success is False
        assert activated_user is None
        
        user.refresh_from_db()
        assert user.is_active is False

    def test_activate_account_invalid_uidb64(self):
        """Test account activation fails with an invalid uidb64."""
        user = UserFactory(is_active=False)
        invalid_uidb64 = "invalid-uidb64"
        token = default_token_generator.make_token(user)

        success, activated_user = AuthService.activate_account(invalid_uidb64, token)

        assert success is False
        assert activated_user is None


@pytest.mark.django_db
class TestCeleryTasks:
    @patch('apps.accounts.tasks.send_mail')
    def test_send_activation_email_task_success(self, mock_send_mail):
        """Test that the activation email task sends an email using Django send_mail."""
        user = UserFactory(email="test@example.com")
        domain = "testserver.com"

        result = send_activation_email_task(user.id, domain)

        assert result == "Activation email sent"
        mock_send_mail.assert_called_once()
        args, kwargs = mock_send_mail.call_args
        # Verify email recipient
        assert args[3] == [user.email]
        # Verify subject
        assert args[0] == 'Aktywuj swoje konto trenera'

    def test_send_activation_email_task_user_not_found(self):
        """Test that task returns error message if user does not exist."""
        result = send_activation_email_task(999999, "testserver.com")
        assert result == "User not found"
