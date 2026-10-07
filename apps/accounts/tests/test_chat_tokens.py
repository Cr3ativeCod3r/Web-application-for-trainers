import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from django.conf import settings
from django.urls import reverse

from apps.accounts.tests.factories import UserFactory


def public_key():
    private = serialization.load_pem_private_key(settings.JWT_PRIVATE_KEY.encode(), password=None)
    return private.public_key()


@pytest.mark.django_db
class TestChatTokenApi:
    url = reverse('accounts:chat_token')

    def test_requires_login(self, client):
        response = client.post(self.url)
        assert response.status_code == 302

    def test_get_is_not_allowed(self, client):
        client.force_login(UserFactory())
        assert client.get(self.url).status_code == 405

    def test_requires_csrf_token(self):
        from django.test import Client

        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(UserFactory())
        assert csrf_client.post(self.url).status_code == 403

    def test_issues_short_lived_token_for_chat_audience(self, client):
        user = UserFactory()
        client.force_login(user)

        response = client.post(self.url)

        assert response.status_code == 200
        assert response['Cache-Control'] == 'no-store'
        data = response.json()
        claims = jwt.decode(
            data['token'], public_key(), algorithms=['ES256'], audience='coachly-chat', issuer='coachly-web'
        )
        assert claims['sub'] == str(user.pk)
        assert claims['exp'] - claims['iat'] == data['expires_in'] == settings.CHAT_TOKEN_LIFETIME
        assert data['expires_in'] <= 15 * 60

    def test_tokens_are_unique(self, client):
        client.force_login(UserFactory())
        first = jwt.decode(client.post(self.url).json()['token'], options={'verify_signature': False})
        second = jwt.decode(client.post(self.url).json()['token'], options={'verify_signature': False})
        assert first['jti'] != second['jti']

    def test_pages_do_not_embed_tokens(self, client):
        client.force_login(UserFactory())
        response = client.get(reverse('accounts:chat'))
        assert response.status_code == 200
        assert b'eyJ' not in response.content  # base64 of '{"' - the start of every JWT
