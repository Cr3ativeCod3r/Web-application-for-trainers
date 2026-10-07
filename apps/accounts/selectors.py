from django.contrib.auth import get_user_model

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
