import json
from unittest.mock import patch

import pytest
from django.urls import reverse

from apps.pages.services import AIServiceError


def post_quiz(client, payload):
    return client.post(reverse('pages:quiz_submit'), data=json.dumps(payload), content_type='application/json')


@pytest.fixture(autouse=True)
def clear_ratelimit_cache():
    from django.core.cache import cache
    cache.clear()


@pytest.mark.django_db
class TestQuizSubmitApi:
    @pytest.mark.parametrize('payload', [{}, {'answers': []}, {'answers': 'x'}, {'answers': [1, 2]}, [1]])
    def test_rejects_invalid_payload(self, client, payload):
        assert post_quiz(client, payload).status_code == 400

    def test_rejects_get(self, client):
        assert client.get(reverse('pages:quiz_submit')).status_code == 405

    @patch('apps.pages.views.get_ai_sport_recommendation')
    def test_truncates_answers_before_calling_ai(self, mock_ai, client):
        mock_ai.return_value = {'recommendation': 'Biegaj!', 'suggested_sport': ''}
        post_quiz(client, {'answers': [{'question': 'Q', 'answer': 'a' * 10_000}]})

        answers = mock_ai.call_args.args[0]
        assert len(answers[0]['answer']) == 500

    @patch('apps.pages.views.get_ai_sport_recommendation', side_effect=AIServiceError('quota exceeded for key AIza...'))
    def test_does_not_leak_ai_error_details(self, _mock_ai, client):
        response = post_quiz(client, {'answers': [{'question': 'Q', 'answer': 'A'}]})
        assert response.status_code == 502
        assert 'AIza' not in response.content.decode()

    @patch('apps.pages.views.get_ai_sport_recommendation')
    def test_is_rate_limited(self, mock_ai, client):
        mock_ai.return_value = {'recommendation': 'ok', 'suggested_sport': ''}
        payload = {'answers': [{'question': 'Q', 'answer': 'A'}]}
        statuses = [post_quiz(client, payload).status_code for _ in range(6)]
        assert statuses[:5] == [200] * 5
        assert statuses[5] == 429

    @patch('apps.pages.views.get_ai_sport_recommendation')
    def test_rate_limit_response_is_json_for_api_calls(self, mock_ai, client):
        mock_ai.return_value = {'recommendation': 'ok', 'suggested_sport': ''}
        payload = {'answers': [{'question': 'Q', 'answer': 'A'}]}
        for _ in range(5):
            post_quiz(client, payload)
        assert 'error' in post_quiz(client, payload).json()
