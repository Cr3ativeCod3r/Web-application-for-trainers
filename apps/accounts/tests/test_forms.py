import pytest

from apps.accounts.forms import ClientRegistrationForm, SinglePasswordSetForm, TrainerRegistrationForm
from apps.accounts.tests.factories import UserFactory


@pytest.mark.django_db
class TestPasswordStrength:
    @pytest.mark.parametrize('password', ['123', '12345678', 'password', 'qwerty123'])
    def test_trainer_registration_rejects_weak_passwords(self, password):
        form = TrainerRegistrationForm(data={'email': 'new@example.com', 'password': password})
        assert not form.is_valid()
        assert 'password' in form.errors

    def test_client_registration_rejects_password_similar_to_email(self):
        form = ClientRegistrationForm(data={
            'email': 'jankowalski@example.com', 'first_name': 'Jan', 'last_name': 'Kowalski',
            'password': 'jankowalski',
        })
        assert not form.is_valid()
        assert 'password' in form.errors

    def test_registration_accepts_strong_password(self):
        form = TrainerRegistrationForm(data={'email': 'new@example.com', 'password': 'Zielony-Rower-42'})
        assert form.is_valid(), form.errors

    def test_password_reset_rejects_weak_password(self):
        form = SinglePasswordSetForm(UserFactory(), data={'new_password1': '123'})
        assert not form.is_valid()
        assert 'new_password1' in form.errors
