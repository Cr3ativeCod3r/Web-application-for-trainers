import pytest
from django.db import connection
from django.urls import reverse

from apps.accounts.models import ClientProfile, TrainerStatus
from apps.accounts.tests.factories import UserFactory
from apps.trainers.tests.factories import TrainerProfileFactory


@pytest.fixture
def chat_rooms_table(db):
    # In production this table is created by the chat service's Alembic migrations.
    with connection.cursor() as cursor:
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS chat_rooms "
            "(id serial PRIMARY KEY, client_id integer NOT NULL, trainer_id integer NOT NULL)"
        )
    return connection


def make_client(email):
    user = UserFactory(email=email, status=TrainerStatus.REGISTERED)
    ClientProfile.objects.create(user=user, first_name='Anna', last_name='Nowak')
    return user


@pytest.mark.django_db
class TestUserInfoApi:
    def test_never_returns_email(self, client, chat_rooms_table):
        viewer = UserFactory()
        trainer = TrainerProfileFactory(user=UserFactory(status=TrainerStatus.APPROVED_TRAINER)).user
        client.force_login(viewer)

        data = client.get(reverse('accounts:user_info_api', args=[trainer.pk])).json()

        assert trainer.email not in str(data)
        assert data['trainer_username'] == trainer.trainer_profile.username

    def test_client_hidden_from_strangers(self, client, chat_rooms_table):
        stranger = UserFactory()
        target = make_client('client@example.com')
        client.force_login(stranger)

        response = client.get(reverse('accounts:user_info_api', args=[target.pk]))

        assert response.status_code == 404

    def test_client_visible_to_chat_partner(self, client, chat_rooms_table):
        trainer = TrainerProfileFactory(user=UserFactory(status=TrainerStatus.APPROVED_TRAINER)).user
        target = make_client('client@example.com')
        with chat_rooms_table.cursor() as cursor:
            cursor.execute(
                "INSERT INTO chat_rooms (client_id, trainer_id) VALUES (%s, %s)", [target.pk, trainer.pk]
            )
        client.force_login(trainer)

        data = client.get(reverse('accounts:user_info_api', args=[target.pk])).json()

        assert data['name'] == 'Anna Nowak'
        assert 'client@example.com' not in str(data)
