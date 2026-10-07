from unittest.mock import patch

import pytest
from django.core import mail
from django.core.cache import cache
from django.urls import reverse

from apps.pages.tasks import send_contact_email_task

VALID = {'name': 'Jan Kowalski', 'email': 'jan@example.com', 'message': 'Dzień dobry & pozdrawiam'}


@pytest.fixture(autouse=True)
def clear_ratelimit_cache():
    cache.clear()


@pytest.mark.django_db
class TestContactView:
    @patch('apps.pages.views.send_contact_email_task.delay')
    def test_valid_form_queues_email(self, mock_delay, client):
        response = client.post(reverse('pages:contact'), VALID)
        assert response.status_code == 302
        mock_delay.assert_called_once_with(**VALID)

    @patch('apps.pages.views.send_contact_email_task.delay')
    def test_rejects_header_injection_in_name(self, mock_delay, client):
        response = client.post(reverse('pages:contact'), {**VALID, 'name': 'Jan\r\nBcc: victim@example.com'})
        assert response.status_code == 200
        mock_delay.assert_not_called()

    @patch('apps.pages.views.send_contact_email_task.delay')
    def test_rejects_invalid_email(self, mock_delay, client):
        client.post(reverse('pages:contact'), {**VALID, 'email': 'not-an-email'})
        mock_delay.assert_not_called()

    @patch('apps.pages.views.send_contact_email_task.delay')
    def test_is_rate_limited(self, _mock_delay, client):
        statuses = [client.post(reverse('pages:contact'), VALID).status_code for _ in range(4)]
        assert statuses == [302, 302, 302, 429]


def test_contact_email_is_readable_utf8_with_reply_to(settings):
    settings.DEFAULT_FROM_EMAIL = 'kontakt@coachly.test'
    send_contact_email_task(**VALID)

    sent = mail.outbox[0]
    assert sent.reply_to == ['jan@example.com']
    assert 'Wiadomość z formularza' in sent.body
    assert 'Dzień dobry & pozdrawiam' in sent.body  # plain text: no HTML escaping
