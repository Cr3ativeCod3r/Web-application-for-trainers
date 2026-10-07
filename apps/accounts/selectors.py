from django.contrib.auth import get_user_model
from django.db import connection

from .models import TrainerStatus

User = get_user_model()


def get_user_display_info(user) -> dict:
    """
    Public display data for a user (name + avatar), used by the chat UI.
    Never includes the e-mail address.
    """
    name = ''
    avatar_url = ''
    trainer_username = None

    profile = getattr(user, 'trainer_profile', None)
    if profile is not None:
        name = profile.full_name
        if profile.profile_picture:
            avatar_url = profile.profile_picture.url
        if user.status == TrainerStatus.APPROVED_TRAINER:
            trainer_username = profile.username
    else:
        client_profile = getattr(user, 'client_profile', None)
        if client_profile is not None:
            name = f"{client_profile.first_name} {client_profile.last_name}".strip()

    return {
        'id': user.pk,
        'name': name or f"Użytkownik #{user.pk}",
        'avatar_url': avatar_url,
        'trainer_username': trainer_username,
    }


def users_share_chat_room(user_a_id: int, user_b_id: int) -> bool:
    """
    True if the two users have a conversation in the chat microservice.

    The chat service owns the `chat_rooms` table (Alembic-managed) but both
    services share one PostgreSQL database, so a read-only query is enough here.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT 1 FROM chat_rooms
            WHERE (client_id = %s AND trainer_id = %s)
               OR (client_id = %s AND trainer_id = %s)
            LIMIT 1
            """,
            [user_a_id, user_b_id, user_b_id, user_a_id],
        )
        return cursor.fetchone() is not None
