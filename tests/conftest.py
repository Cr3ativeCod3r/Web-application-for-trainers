import pytest
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.fixture
def test_user(db):
    user = User.objects.create_user(
        email="test@example.com",
        password="testpassword123",
        is_active=True
    )
    return user

@pytest.fixture
def inactive_user(db):
    user = User.objects.create_user(
        email="inactive@example.com",
        password="testpassword123",
        is_active=False
    )
    return user
