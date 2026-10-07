import pytest
from django.urls import reverse

from apps.accounts.models import TrainerStatus
from apps.accounts.tests.factories import UserFactory
from apps.trainers.tests.factories import TrainerProfileFactory


@pytest.mark.django_db
class TestTrainersViews:
    def test_home_search_view_get(self, client):
        """Test GET request to home search view."""
        url = reverse('trainers:home_search')
        response = client.get(url)
        assert response.status_code == 200
        assert 'trainers' in response.context

    def test_autocomplete_view_sport(self, client):
        """Test autocomplete endpoint returns JSON data."""
        # Create approved trainer to show up in suggestions
        from apps.trainers.models import Sport
        sport_bieganie = Sport.objects.create(name="Bieganie")
        u = UserFactory(status=TrainerStatus.APPROVED_TRAINER)
        TrainerProfileFactory(user=u, sports=[sport_bieganie])

        url = reverse('trainers:autocomplete')
        response = client.get(url, {'type': 'sport', 'q': 'bieg'})
        assert response.status_code == 200
        json_data = response.json()
        assert 'results' in json_data
        assert 'Bieganie' in json_data['results']

    def test_public_profile_view_approved(self, client):
        """Test that public profile view works for approved trainers."""
        u = UserFactory(status=TrainerStatus.APPROVED_TRAINER)
        profile = TrainerProfileFactory(user=u)

        url = reverse('trainers:public_profile', kwargs={'username': profile.username})
        response = client.get(url)
        assert response.status_code == 200
        assert response.context['profile'] == profile

    def test_public_profile_view_not_approved(self, client):
        """Test that public profile view returns 404 for non-approved trainers."""
        u = UserFactory(status=TrainerStatus.PENDING_APPLICATION)
        profile = TrainerProfileFactory(user=u)

        url = reverse('trainers:public_profile', kwargs={'username': profile.username})
        response = client.get(url)
        assert response.status_code == 404

    def test_apply_view_anonymous_redirect(self, client):
        """Test that anonymous users are redirected to login when applying."""
        url = reverse('trainers:apply')
        response = client.get(url)
        assert response.status_code == 302
        assert response.url.startswith(reverse('accounts:login'))

    def test_apply_view_registered_user(self, client):
        """Test registered user can access application page."""
        user = UserFactory(status=TrainerStatus.REGISTERED, is_active=True)
        client.force_login(user)

        url = reverse('trainers:apply')
        response = client.get(url)
        assert response.status_code == 200

    def test_apply_view_already_trainer_redirect(self, client):
        """Test that already applied or approved users are redirected."""
        user = UserFactory(status=TrainerStatus.APPROVED_TRAINER, is_active=True)
        client.force_login(user)

        url = reverse('trainers:apply')
        response = client.get(url)
        assert response.status_code == 302
        assert response.url == reverse('trainers:home_search')

    def test_trainer_account_view_without_profile(self, client):
        """Test that user without a profile is redirected to apply."""
        user = UserFactory(status=TrainerStatus.REGISTERED, is_active=True)
        client.force_login(user)

        url = reverse('trainers:account')
        response = client.get(url)
        assert response.status_code == 302
        assert response.url == reverse('trainers:apply')

    def test_trainer_account_view_with_profile(self, client):
        """Test that trainer with a profile can access account page."""
        user = UserFactory(status=TrainerStatus.APPROVED_TRAINER, is_active=True)
        profile = TrainerProfileFactory(user=user)
        client.force_login(user)

        url = reverse('trainers:account')
        response = client.get(url)
        assert response.status_code == 200
        assert response.context['profile'] == profile


@pytest.mark.django_db
def test_failed_application_leaves_nothing_behind(client):
    """
    The view writes in several steps (status + profile, then sports via save_m2m).
    If anything fails after the first write, the request transaction must roll
    everything back instead of leaving a half-created application.
    """
    from unittest.mock import patch

    from apps.trainers.models import Sport, TrainerProfile

    user = UserFactory(status=TrainerStatus.REGISTERED, is_active=True)
    client.force_login(user)
    sport = Sport.objects.create(name='Boks')
    data = {
        'username': 'jan-trener', 'full_name': 'Jan', 'sports': [sport.pk], 'location': 'Kraków',
        'headline': 'Trener', 'description': 'Opis', 'hourly_rate': '100',
        'contact_email': 'jan@example.com', 'training_type': 'STATIONARY', 'gender': 'M',
    }

    # Fail at the last step of the view, after every write has been issued.
    with patch('apps.trainers.views.messages.success', side_effect=RuntimeError('boom')):
        with pytest.raises(RuntimeError):
            client.post(reverse('trainers:apply'), data)

    user.refresh_from_db()
    assert user.status == TrainerStatus.REGISTERED
    assert not TrainerProfile.objects.filter(user=user).exists()
