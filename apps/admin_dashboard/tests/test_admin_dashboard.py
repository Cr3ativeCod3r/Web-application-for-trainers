import pytest
from django.urls import reverse

from apps.accounts.models import TrainerStatus
from apps.accounts.tests.factories import UserFactory
from apps.admin_dashboard.selectors import get_admin_dashboard_data
from apps.trainers.tests.factories import (
    TrainerPostFactory,
    TrainerProfileFactory,
    TrainerProfileUpdateFactory,
)


@pytest.mark.django_db
class TestAdminDashboardSelectors:
    def test_get_admin_dashboard_data(self):
        """Test admin dashboard filters data properly."""
        user_p = UserFactory(status=TrainerStatus.PENDING_APPLICATION, email="pending@test.com")
        TrainerProfileFactory(user=user_p)

        user_a = UserFactory(status=TrainerStatus.APPROVED_TRAINER, email="active@test.com")
        profile_a = TrainerProfileFactory(user=user_a)

        user_b = UserFactory(status=TrainerStatus.BANNED, email="banned@test.com")
        TrainerProfileFactory(user=user_b)

        TrainerProfileUpdateFactory(profile=profile_a)
        TrainerPostFactory(trainer=profile_a, title="Wspanialy post")

        dashboard_data = get_admin_dashboard_data()

        assert dashboard_data['pending_profiles'].count() == 1
        assert dashboard_data['active_profiles'].count() == 1
        assert dashboard_data['banned_profiles'].count() == 1
        assert dashboard_data['pending_updates'].count() == 1
        assert dashboard_data['all_posts'].count() == 1

        # Test search filtering
        filtered_data = get_admin_dashboard_data(q_active="active@test.com")
        assert filtered_data['active_profiles'].count() == 1

        filtered_data = get_admin_dashboard_data(q_active="nonexistent")
        assert filtered_data['active_profiles'].count() == 0


@pytest.mark.django_db
class TestAdminDashboardViews:
    def test_dashboard_staff_only(self, client):
        """Test that non-staff users cannot access admin dashboard."""
        user = UserFactory(is_staff=False, is_active=True)
        client.force_login(user)

        url = reverse('admin_dashboard:dashboard')
        response = client.get(url)
        assert response.status_code == 302
        assert 'admin/login' in response.url

    def test_dashboard_success_for_staff(self, client):
        """Test that staff users can access admin dashboard."""
        admin = UserFactory(is_staff=True, is_active=True, status=TrainerStatus.ADMIN)
        client.force_login(admin)

        url = reverse('admin_dashboard:dashboard')
        response = client.get(url)
        assert response.status_code == 200
        assert 'pending_profiles' in response.context

    def test_approve_trainer_view(self, client):
        """Test approving a trainer from the admin dashboard."""
        admin = UserFactory(is_staff=True, is_active=True, status=TrainerStatus.ADMIN)
        client.force_login(admin)

        user = UserFactory(status=TrainerStatus.PENDING_APPLICATION)
        profile = TrainerProfileFactory(user=user)

        url = reverse('admin_dashboard:approve_trainer', kwargs={'profile_id': profile.id})
        response = client.post(url)
        assert response.status_code == 302

        user.refresh_from_db()
        assert user.status == TrainerStatus.APPROVED_TRAINER

    def test_approve_update_view(self, client):
        """Test approving a profile update from the admin dashboard."""
        admin = UserFactory(is_staff=True, is_active=True, status=TrainerStatus.ADMIN)
        client.force_login(admin)

        profile = TrainerProfileFactory(full_name="Original Name")
        update = TrainerProfileUpdateFactory(profile=profile, full_name="Updated Name")

        url = reverse('admin_dashboard:approve_update', kwargs={'update_id': update.id})
        response = client.post(url)
        assert response.status_code == 302

        profile.refresh_from_db()
        assert profile.full_name == "Updated Name"

    def test_reject_update_view(self, client):
        """Test rejecting a profile update from the admin dashboard."""
        admin = UserFactory(is_staff=True, is_active=True, status=TrainerStatus.ADMIN)
        client.force_login(admin)

        profile = TrainerProfileFactory(full_name="Original Name")
        update = TrainerProfileUpdateFactory(profile=profile, full_name="Updated Name")

        url = reverse('admin_dashboard:reject_update', kwargs={'update_id': update.id})
        response = client.post(url)
        assert response.status_code == 302

        profile.refresh_from_db()
        assert profile.full_name == "Original Name"


@pytest.mark.django_db
class TestAdminDashboardStateChangingActions:
    @pytest.fixture
    def admin_client(self, client):
        admin = UserFactory(is_staff=True, is_superuser=True, is_active=True, status=TrainerStatus.ADMIN)
        client.force_login(admin)
        return client

    def test_approve_trainer_rejects_get(self, admin_client):
        """State changes over GET could be triggered by a link/image on any page (CSRF)."""
        user = UserFactory(status=TrainerStatus.PENDING_APPLICATION)
        profile = TrainerProfileFactory(user=user)

        url = reverse('admin_dashboard:approve_trainer', kwargs={'profile_id': profile.id})
        response = admin_client.get(url)

        assert response.status_code == 405
        user.refresh_from_db()
        assert user.status == TrainerStatus.PENDING_APPLICATION

    def test_approve_missing_profile_returns_404(self, admin_client):
        url = reverse('admin_dashboard:approve_trainer', kwargs={'profile_id': 999999})
        assert admin_client.post(url).status_code == 404

    def test_ban_and_unban_trainer(self, admin_client):
        user = UserFactory(status=TrainerStatus.APPROVED_TRAINER, is_active=True)
        profile = TrainerProfileFactory(user=user)

        admin_client.post(reverse('admin_dashboard:ban_trainer', kwargs={'profile_id': profile.id}))
        user.refresh_from_db()
        assert user.status == TrainerStatus.BANNED
        assert user.is_active is False

        admin_client.post(reverse('admin_dashboard:unban_trainer', kwargs={'profile_id': profile.id}))
        user.refresh_from_db()
        assert user.status == TrainerStatus.APPROVED_TRAINER
        assert user.is_active is True

    def test_unban_of_pending_account_is_refused(self, admin_client):
        user = UserFactory(status=TrainerStatus.PENDING_APPLICATION)
        profile = TrainerProfileFactory(user=user)

        response = admin_client.post(reverse('admin_dashboard:unban_trainer', kwargs={'profile_id': profile.id}))

        assert response.status_code == 302
        user.refresh_from_db()
        assert user.status == TrainerStatus.PENDING_APPLICATION
