import pytest

from apps.accounts.models import InvalidStatusTransition, TrainerStatus
from apps.accounts.tests.factories import UserFactory
from apps.trainers.models import TrainerProfileUpdate
from apps.trainers.services import (
    apply_for_trainer,
    approve_profile_update,
    approve_trainer,
    ban_trainer,
    reject_profile_update,
    unban_trainer,
)
from apps.trainers.tests.factories import TrainerProfileFactory, TrainerProfileUpdateFactory


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

    def test_approve_profile_update_copies_gender_and_training_type(self):
        """Regression: gender and training_type used to be silently dropped on approval."""
        profile = TrainerProfileFactory(gender='M', training_type='STATIONARY')
        update_req = TrainerProfileUpdateFactory(profile=profile, gender='F', training_type='ONLINE')

        approve_profile_update(update_req)

        profile.refresh_from_db()
        assert profile.gender == 'F'
        assert profile.training_type == 'ONLINE'

    def test_reject_profile_update(self):
        """Test rejecting a profile update deletes the update request without altering main profile."""
        profile = TrainerProfileFactory(full_name="Original Name")
        update_req = TrainerProfileUpdateFactory(profile=profile, full_name="Updated Name")

        reject_profile_update(update_req)

        profile.refresh_from_db()
        assert profile.full_name == "Original Name"
        assert not TrainerProfileUpdate.objects.filter(pk=update_req.pk).exists()


@pytest.mark.django_db
class TestTrainerStatusServices:
    def test_cannot_approve_banned_trainer(self):
        profile = TrainerProfileFactory(user=UserFactory(status=TrainerStatus.BANNED, is_active=False))
        with pytest.raises(InvalidStatusTransition):
            approve_trainer(profile)
        profile.user.refresh_from_db()
        assert profile.user.status == TrainerStatus.BANNED

    def test_unban_requires_banned_account(self):
        """Regression: unban used to promote any account (even a pending one) to trainer."""
        profile = TrainerProfileFactory(user=UserFactory(status=TrainerStatus.PENDING_APPLICATION))
        with pytest.raises(InvalidStatusTransition):
            unban_trainer(profile)
        profile.user.refresh_from_db()
        assert profile.user.status == TrainerStatus.PENDING_APPLICATION

    def test_ban_deactivates_account(self):
        profile = TrainerProfileFactory(user=UserFactory(status=TrainerStatus.APPROVED_TRAINER))
        ban_trainer(profile)
        profile.user.refresh_from_db()
        assert profile.user.status == TrainerStatus.BANNED
        assert profile.user.is_active is False

    def test_apply_twice_is_rejected(self):
        user = UserFactory(status=TrainerStatus.PENDING_APPLICATION)
        with pytest.raises(InvalidStatusTransition):
            apply_for_trainer(user, TrainerProfileFactory.build(user=user))
