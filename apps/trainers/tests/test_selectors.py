import pytest
from apps.accounts.tests.factories import UserFactory
from apps.accounts.models import TrainerStatus
from apps.trainers.tests.factories import TrainerProfileFactory, TrainerProfileUpdateFactory, TrainerPostFactory
from apps.trainers.selectors import (
    get_approved_trainers,
    search_trainers,
    get_autocomplete_suggestions,
    get_admin_dashboard_data,
)

@pytest.mark.django_db
class TestTrainersSelectors:
    def test_get_approved_trainers(self):
        """Test that get_approved_trainers returns only approved trainers."""
        user_approved = UserFactory(status=TrainerStatus.APPROVED_TRAINER)
        profile_approved = TrainerProfileFactory(user=user_approved)

        user_pending = UserFactory(status=TrainerStatus.PENDING_APPLICATION)
        TrainerProfileFactory(user=user_pending)

        approved = get_approved_trainers()
        assert approved.count() == 1
        assert approved.first() == profile_approved

    def test_search_trainers(self):
        """Test searching trainers by sport, location, and type."""
        u1 = UserFactory(status=TrainerStatus.APPROVED_TRAINER)
        p1 = TrainerProfileFactory(user=u1, sport="Joga, Pilates", location="Warszawa", training_type="ONLINE")

        u2 = UserFactory(status=TrainerStatus.APPROVED_TRAINER)
        p2 = TrainerProfileFactory(user=u2, sport="Boks", location="Krakow", training_type="STATIONARY")

        u3 = UserFactory(status=TrainerStatus.APPROVED_TRAINER)
        p3 = TrainerProfileFactory(user=u3, sport="Boks, Crossfit", location="Warszawa", training_type="BOTH")

        # 1. Search by sport
        results = search_trainers(sport="Boks")
        assert results.count() == 2
        assert p2 in results and p3 in results

        # 2. Search by location
        results = search_trainers(location="Warszawa")
        assert results.count() == 2
        assert p1 in results and p3 in results

        # 3. Search by training type
        results = search_trainers(training_type="ONLINE")
        # should include ONLINE and BOTH
        assert results.count() == 2
        assert p1 in results and p3 in results

        # 4. Search combined
        results = search_trainers(sport="Boks", location="Warszawa")
        assert results.count() == 1
        assert results.first() == p3

    def test_get_autocomplete_suggestions(self):
        """Test autocomplete suggestions for sports and locations."""
        u1 = UserFactory(status=TrainerStatus.APPROVED_TRAINER)
        TrainerProfileFactory(user=u1, sport="Pilates, Joga", location="Warszawa")

        u2 = UserFactory(status=TrainerStatus.APPROVED_TRAINER)
        TrainerProfileFactory(user=u2, sport="Joga, Rozciaganie", location="Wroclaw")

        # Autocomplete sport
        suggestions = get_autocomplete_suggestions('sport', 'joga')
        assert "Joga" in suggestions

        # Autocomplete location
        suggestions = get_autocomplete_suggestions('location', 'warsz')
        assert "Warszawa" in suggestions

    def test_get_admin_dashboard_data(self):
        """Test admin dashboard filters data properly."""
        user_p = UserFactory(status=TrainerStatus.PENDING_APPLICATION, email="pending@test.com")
        TrainerProfileFactory(user=user_p)

        user_a = UserFactory(status=TrainerStatus.APPROVED_TRAINER, email="active@test.com")
        profile_a = TrainerProfileFactory(user=user_a)

        user_b = UserFactory(status=TrainerStatus.BANNED, email="banned@test.com")
        TrainerProfileFactory(user=user_b)

        update = TrainerProfileUpdateFactory(profile=profile_a)
        post = TrainerPostFactory(trainer=profile_a, title="Wspanialy post")

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
