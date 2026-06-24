import pytest
from apps.accounts.tests.factories import UserFactory
from apps.accounts.models import TrainerStatus
from apps.trainers.tests.factories import TrainerProfileFactory
from apps.trainers.selectors import (
    get_approved_trainers,
    search_trainers,
    get_autocomplete_suggestions,
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
        from apps.trainers.models import Sport
        sport_joga = Sport.objects.create(name="Joga")
        sport_pilates = Sport.objects.create(name="Pilates")
        sport_boks = Sport.objects.create(name="Boks")
        sport_crossfit = Sport.objects.create(name="Crossfit")

        u1 = UserFactory(status=TrainerStatus.APPROVED_TRAINER)
        p1 = TrainerProfileFactory(user=u1, sports=[sport_joga, sport_pilates], location="Warszawa", training_type="ONLINE")

        u2 = UserFactory(status=TrainerStatus.APPROVED_TRAINER)
        p2 = TrainerProfileFactory(user=u2, sports=[sport_boks], location="Krakow", training_type="STATIONARY")

        u3 = UserFactory(status=TrainerStatus.APPROVED_TRAINER)
        p3 = TrainerProfileFactory(user=u3, sports=[sport_boks, sport_crossfit], location="Warszawa", training_type="BOTH")

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
        from apps.trainers.models import Sport
        sport_pilates = Sport.objects.create(name="Pilates")
        sport_joga = Sport.objects.create(name="Joga")
        sport_rozciaganie = Sport.objects.create(name="Rozciaganie")

        u1 = UserFactory(status=TrainerStatus.APPROVED_TRAINER)
        TrainerProfileFactory(user=u1, sports=[sport_pilates, sport_joga], location="Warszawa")

        u2 = UserFactory(status=TrainerStatus.APPROVED_TRAINER)
        TrainerProfileFactory(user=u2, sports=[sport_joga, sport_rozciaganie], location="Wroclaw")

        # Autocomplete sport
        suggestions = get_autocomplete_suggestions('sport', 'joga')
        assert "Joga" in suggestions

        # Autocomplete location
        suggestions = get_autocomplete_suggestions('location', 'warsz')
        assert "Warszawa" in suggestions
