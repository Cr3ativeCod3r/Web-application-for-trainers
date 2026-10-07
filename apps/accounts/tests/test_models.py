import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import InvalidStatusTransition, StatusTransition, TrainerStatus
from apps.accounts.tests.factories import UserFactory

User = get_user_model()

@pytest.mark.django_db
class TestCustomUserModel:
    def test_create_user_successful(self):
        """Test successful creation of a regular user."""
        email = "test@example.com"
        password = "securepassword123"
        user = User.objects.create_user(email=email, password=password)

        assert user.email == email
        assert user.check_password(password) is True
        assert user.status == TrainerStatus.REGISTERED
        assert user.is_active is False
        assert user.is_staff is False
        assert user.is_superuser is False
        assert str(user) == email

    def test_create_user_missing_email(self):
        """Test that user creation raises ValueError if email is missing."""
        with pytest.raises(ValueError) as exc_info:
            User.objects.create_user(email="")
        assert str(exc_info.value) == "Adres email jest wymagany"

    def test_create_superuser_successful(self):
        """Test successful creation of a superuser."""
        email = "admin@example.com"
        password = "adminpassword123"
        admin_user = User.objects.create_superuser(email=email, password=password)

        assert admin_user.email == email
        assert admin_user.check_password(password) is True
        assert admin_user.status == TrainerStatus.ADMIN
        assert admin_user.is_active is True
        assert admin_user.is_staff is True
        assert admin_user.is_superuser is True


@pytest.mark.django_db
class TestStatusTransitions:
    @pytest.mark.parametrize('current,transition,expected', [
        (TrainerStatus.REGISTERED, StatusTransition.APPLY, TrainerStatus.PENDING_APPLICATION),
        (TrainerStatus.PENDING_APPLICATION, StatusTransition.APPROVE, TrainerStatus.APPROVED_TRAINER),
        (TrainerStatus.APPROVED_TRAINER, StatusTransition.BAN, TrainerStatus.BANNED),
        (TrainerStatus.BANNED, StatusTransition.UNBAN, TrainerStatus.APPROVED_TRAINER),
    ])
    def test_allowed_transitions(self, current, transition, expected):
        user = UserFactory(status=current)
        user.apply_transition(transition)
        assert user.status == expected

    @pytest.mark.parametrize('current,transition', [
        (TrainerStatus.REGISTERED, StatusTransition.APPROVE),
        (TrainerStatus.BANNED, StatusTransition.APPROVE),
        (TrainerStatus.PENDING_APPLICATION, StatusTransition.UNBAN),
        (TrainerStatus.PENDING_APPLICATION, StatusTransition.BAN),
        (TrainerStatus.PENDING_APPLICATION, StatusTransition.APPLY),
        (TrainerStatus.ADMIN, StatusTransition.BAN),
    ])
    def test_forbidden_transitions(self, current, transition):
        user = UserFactory(status=current)
        with pytest.raises(InvalidStatusTransition):
            user.apply_transition(transition)
        assert user.status == current
