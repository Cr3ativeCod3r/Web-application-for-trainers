import pytest
from django.urls import reverse
from apps.accounts.tests.factories import UserFactory
from apps.accounts.models import TrainerStatus
from apps.trainers.tests.factories import TrainerProfileFactory, TrainerPostFactory
from apps.trainers.models import TrainerProfile

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
        u = UserFactory(status=TrainerStatus.APPROVED_TRAINER)
        TrainerProfileFactory(user=u, sport="Bieganie")

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
