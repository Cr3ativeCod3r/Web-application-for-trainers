import json
from unittest.mock import patch

import fakeredis
import pytest
from django.db import transaction

from apps.accounts.models import TrainerStatus
from apps.accounts.tests.factories import UserFactory
from apps.events.contracts import USER_DELETED, USER_EVENTS_STREAM, USER_UPDATED
from apps.events.models import OutboxEvent
from apps.events.services import purge_published_events, relay_pending_events
from apps.trainers.services import ban_trainer
from apps.trainers.tests.factories import TrainerProfileFactory


@pytest.fixture
def bus():
    fake = fakeredis.FakeRedis(decode_responses=True)
    with patch('apps.events.services.get_bus', return_value=fake):
        yield fake


def user_events(user_id):
    return OutboxEvent.objects.filter(aggregate_id=str(user_id)).order_by('id')


@pytest.mark.django_db
class TestRecordingUserEvents:
    def test_ban_records_snapshot_of_inactive_user(self):
        profile = TrainerProfileFactory(user=UserFactory(status=TrainerStatus.APPROVED_TRAINER))
        OutboxEvent.objects.all().delete()

        ban_trainer(profile)

        event = user_events(profile.user_id).last()
        assert event.event_type == USER_UPDATED
        assert event.payload['is_active'] is False
        assert event.payload['accepts_new_conversations'] is False

    def test_snapshot_exposes_public_data_only(self):
        profile = TrainerProfileFactory(user=UserFactory(status=TrainerStatus.APPROVED_TRAINER))

        payload = user_events(profile.user_id).last().payload

        assert payload['display_name'] == profile.full_name
        assert payload['trainer_username'] == profile.username
        assert payload['accepts_new_conversations'] is True
        assert profile.user.email not in json.dumps(payload)

    def test_last_login_update_is_not_an_event(self):
        user = UserFactory()
        before = user_events(user.pk).count()

        user.save(update_fields=['last_login'])

        assert user_events(user.pk).count() == before

    def test_deleting_user_records_tombstone(self):
        user = UserFactory()
        user_id = user.pk
        user.delete()
        assert user_events(user_id).last().event_type == USER_DELETED

    def test_rolled_back_change_leaves_no_event(self):
        user = UserFactory()
        before = user_events(user.pk).count()

        with pytest.raises(RuntimeError), transaction.atomic():
            user.is_active = False
            user.save()
            raise RuntimeError

        assert user_events(user.pk).count() == before

    def test_relay_is_scheduled_only_after_commit(self, django_capture_on_commit_callbacks):
        with patch('apps.events.tasks.relay_outbox_events.delay') as delay:
            with django_capture_on_commit_callbacks(execute=True):
                UserFactory()
                delay.assert_not_called()
            delay.assert_called()


@pytest.mark.django_db
class TestRelay:
    def test_publishes_pending_events_in_order_and_marks_them(self, bus):
        user = UserFactory()
        expected_ids = list(user_events(user.pk).values_list('id', flat=True))

        published = relay_pending_events()

        assert published == OutboxEvent.objects.count()
        entries = bus.xrange(USER_EVENTS_STREAM)
        ids = [int(fields['id']) for _, fields in entries]
        assert ids == sorted(ids)
        assert set(expected_ids) <= set(ids)
        assert not OutboxEvent.objects.filter(published_at__isnull=True).exists()

        last = json.loads(entries[-1][1]['payload'])
        assert last['user_id'] == user.pk

    def test_failed_publish_keeps_events_for_retry(self, bus):
        UserFactory()
        with patch.object(bus, 'pipeline', side_effect=ConnectionError('redis down')):
            with pytest.raises(ConnectionError):
                relay_pending_events()

        assert OutboxEvent.objects.filter(published_at__isnull=True).exists()
        assert relay_pending_events() > 0

    def test_second_run_publishes_nothing(self, bus):
        UserFactory()
        relay_pending_events()
        assert relay_pending_events() == 0

    def test_purge_removes_only_old_published_events(self, bus):
        UserFactory()
        relay_pending_events()
        OutboxEvent.objects.update(published_at='2000-01-01T00:00:00Z')
        UserFactory()  # unpublished

        purge_published_events(older_than_days=7)

        assert OutboxEvent.objects.exists()
        assert not OutboxEvent.objects.filter(published_at__isnull=False).exists()


@pytest.mark.django_db
class TestAvatarInSnapshot:
    def test_snapshot_uses_stable_avatar_url(self, client):
        from django.core.files.uploadedfile import SimpleUploadedFile

        profile = TrainerProfileFactory(user=UserFactory(status=TrainerStatus.APPROVED_TRAINER))
        profile.profile_picture = SimpleUploadedFile('me.png', b'fake-image', content_type='image/png')
        profile.save()

        avatar_url = user_events(profile.user_id).last().payload['avatar_url']

        assert avatar_url.startswith(f'/api/avatar/{profile.user_id}/?v=')
        response = client.get(avatar_url)
        assert response.status_code == 302
        assert response.url == profile.profile_picture.url

    def test_avatar_of_non_approved_user_is_not_served(self, client):
        from django.core.files.uploadedfile import SimpleUploadedFile

        profile = TrainerProfileFactory(user=UserFactory(status=TrainerStatus.PENDING_APPLICATION))
        profile.profile_picture = SimpleUploadedFile('me.png', b'fake-image', content_type='image/png')
        profile.save()

        assert client.get(f'/api/avatar/{profile.user_id}/').status_code == 404
