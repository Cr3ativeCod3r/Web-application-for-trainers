import pytest
from unittest.mock import patch
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator

from apps.accounts.tests.factories import UserFactory

User = get_user_model()

@pytest.mark.django_db
class TestAccountViews:
    def test_register_view_get(self, client):
        """Test GET request to registration view."""
        url = reverse('accounts:register')
        response = client.get(url)
        assert response.status_code == 200
        assert 'form' in response.context

    @patch('apps.accounts.services.send_activation_email_task.delay')
    def test_register_view_post_success(self, mock_send_email_task, client):
        """Test registration POST request with valid data."""
        url = reverse('accounts:register')
        data = {
            'email': 'newtrainer@example.com',
            'password': 'strongpassword123'
        }
        response = client.post(url, data)
        assert response.status_code == 302
        assert response.url == reverse('accounts:registration_success')

        # Check user was created and is inactive
        user = User.objects.get(email='newtrainer@example.com')
        assert user.is_active is False
        mock_send_email_task.assert_called_once()

    def test_register_view_authenticated_redirect(self, client):
        """Test that authenticated users are redirected away from registration."""
        user = UserFactory(is_active=True)
        client.force_login(user)

        url = reverse('accounts:register')
        response = client.get(url)
        assert response.status_code == 302
        assert response.url == reverse('trainers:home_search')

    def test_login_view_get(self, client):
        """Test GET request to login view."""
        url = reverse('accounts:login')
        response = client.get(url)
        assert response.status_code == 200
        assert 'form' in response.context

    def test_login_view_post_success(self, client):
        """Test login POST request with valid credentials."""
        password = 'testpassword123'
        user = UserFactory(is_active=True)  # must be active to login
        user.set_password(password)
        user.save()

        url = reverse('accounts:login')
        data = {
            'username': user.email,
            'password': password
        }
        response = client.post(url, data)
        assert response.status_code == 302
        assert response.url == reverse('trainers:home_search')

    def test_login_view_post_inactive_user(self, client):
        """Test login attempts with an inactive user fail."""
        password = 'testpassword123'
        user = UserFactory(is_active=False)
        user.set_password(password)
        user.save()

        url = reverse('accounts:login')
        data = {
            'username': user.email,
            'password': password
        }
        response = client.post(url, data)
        assert response.status_code == 200  # returns same page with error
        form = response.context['form']
        assert len(form.errors) > 0
        assert 'inactive' in form.error_messages

    def test_activate_account_view_success(self, client):
        """Test GET request to activate account view with valid token."""
        user = UserFactory(is_active=False)
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        url = reverse('accounts:activate', kwargs={'uidb64': uidb64, 'token': token})
        response = client.get(url)

        assert response.status_code == 302
        assert response.url == reverse('accounts:login')

        # Check messages
        messages = [m.message for m in get_messages(response.wsgi_request)]
        assert len(messages) > 0
        assert 'Twoje konto zostało aktywowane. Możesz się teraz zalogować.' in messages

        user.refresh_from_db()
        assert user.is_active is True

    def test_activate_account_view_failure(self, client):
        """Test GET request to activate account view with invalid token."""
        user = UserFactory(is_active=False)
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        invalid_token = 'invalid-token'

        url = reverse('accounts:activate', kwargs={'uidb64': uidb64, 'token': invalid_token})
        response = client.get(url)

        assert response.status_code == 302
        assert response.url == reverse('accounts:login')

        messages = [m.message for m in get_messages(response.wsgi_request)]
        assert len(messages) > 0
        assert 'Link aktywacyjny jest nieprawidłowy lub wygasł.' in messages

        user.refresh_from_db()
        assert user.is_active is False
