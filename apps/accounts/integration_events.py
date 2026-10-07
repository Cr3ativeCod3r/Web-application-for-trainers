"""
Publishes the public view of a user to other services (currently: chat).

Other services keep their own copy of this data instead of reading our tables.
Every event carries a full snapshot (not a diff), so a consumer that missed some
events converges as soon as it receives the next one.
"""
import hashlib

from django.contrib.auth import get_user_model
from django.db import transaction
from django.urls import reverse

from apps.events.contracts import USER_DELETED, USER_EVENTS_STREAM, USER_UPDATED
from apps.events.services import record_event

from .models import TrainerStatus
from .selectors import get_user_display_info

User = get_user_model()

SNAPSHOT_SCHEMA_VERSION = 1


def stable_avatar_url(user) -> str:
    """
    A URL that stays valid for as long as the picture exists. The storage URL
    itself cannot be shared with other services: on R2/S3 without a custom domain
    it is a signed URL that expires after an hour. The version parameter changes
    with the file, so caches pick up a new picture.
    """
    profile = getattr(user, 'trainer_profile', None)
    if profile is None or not profile.profile_picture:
        return ''
    version = hashlib.sha256(profile.profile_picture.name.encode()).hexdigest()[:12]
    return f"{reverse('accounts:avatar', args=[user.pk])}?v={version}"


def build_user_snapshot(user) -> dict:
    info = get_user_display_info(user)
    return {
        'schema_version': SNAPSHOT_SCHEMA_VERSION,
        'user_id': user.pk,
        'display_name': info['name'],
        'avatar_url': stable_avatar_url(user),
        'trainer_username': info['trainer_username'],
        'is_active': user.is_active,
        # Clients may only open conversations with approved, active trainers.
        'accepts_new_conversations': user.is_active and user.status == TrainerStatus.APPROVED_TRAINER,
    }


def publish_user_updated(user_id: int) -> None:
    with transaction.atomic():
        # Lock the row so that events for one user are recorded in commit order:
        # the outbox id is the version consumers compare, and it must not go
        # backwards relative to the state it describes.
        user = (
            User.objects.select_for_update(of=('self',))
            .select_related('trainer_profile', 'client_profile')
            .filter(pk=user_id)
            .first()
        )
        if user is None:
            return
        record_event(
            stream=USER_EVENTS_STREAM,
            event_type=USER_UPDATED,
            aggregate_id=user.pk,
            payload=build_user_snapshot(user),
        )


def publish_user_deleted(user_id: int) -> None:
    record_event(
        stream=USER_EVENTS_STREAM,
        event_type=USER_DELETED,
        aggregate_id=user_id,
        payload={'schema_version': SNAPSHOT_SCHEMA_VERSION, 'user_id': user_id},
    )
