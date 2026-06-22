import pytest
from apps.accounts.tests.factories import UserFactory
from apps.accounts.models import TrainerStatus
from apps.trainers.tests.factories import TrainerProfileFactory, TrainerProfileUpdateFactory
from apps.trainers.models import TrainerProfile, TrainerProfileUpdate
from apps.trainers.services import (
    apply_for_trainer,
    approve_trainer,
    approve_profile_update,
    reject_profile_update,
)

@pytest.mark.django_db
class TestTrainersServices:
    def test_apply_for_trainer(self):
        """Test applying for a trainer updates user status to pending."""
        user = UserFactory(status=TrainerStatus.REGISTERED)
        profile = TrainerProfileFactory.build(user=user)

        result_profile = apply_for_trainer(user, profile)

        assert result_profile.pk is not None
        assert result_profile.user == user
        user.refresh_from_db()
        assert user.status == TrainerStatus.PENDING_APPLICATION

    def test_approve_trainer(self):
        """Test approving trainer application updates user status to approved."""
        user = UserFactory(status=TrainerStatus.PENDING_APPLICATION)
        profile = TrainerProfileFactory(user=user)

        result_profile = approve_trainer(profile)

        assert result_profile.pk == profile.pk
        user.refresh_from_db()
        assert user.status == TrainerStatus.APPROVED_TRAINER

    def test_approve_profile_update(self):
        """Test approving a profile update copies all fields and deletes the update request."""
        profile = TrainerProfileFactory(full_name="Original Name", location="Original City")
        update_req = TrainerProfileUpdateFactory(
            profile=profile,
            full_name="Updated Name",
            location="Updated City",
            hourly_rate=150.00
        )

        result_profile = approve_profile_update(update_req)

        # Main profile fields should be updated
        assert result_profile.full_name == "Updated Name"
        assert result_profile.location == "Updated City"
        assert float(result_profile.hourly_rate) == 150.00

        # Update request object should be deleted
        assert not TrainerProfileUpdate.objects.filter(pk=update_req.pk).exists()

    def test_reject_profile_update(self):
        """Test rejecting a profile update deletes the update request without altering main profile."""
        profile = TrainerProfileFactory(full_name="Original Name")
        update_req = TrainerProfileUpdateFactory(profile=profile, full_name="Updated Name")

        reject_profile_update(update_req)

        profile.refresh_from_db()
        assert profile.full_name == "Original Name"
        assert not TrainerProfileUpdate.objects.filter(pk=update_req.pk).exists()
