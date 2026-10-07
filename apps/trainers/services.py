import os

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db import transaction

from apps.accounts.models import StatusTransition

from .models import TrainerProfile, TrainerProfileContent, TrainerProfileUpdate

User = get_user_model()


def _locked_user(user):
    """
    Re-read the user with a row lock. Two admins clicking "approve" and "ban" at the
    same time must not both pass the transition check against the same stale status.
    """
    return User.objects.select_for_update().get(pk=user.pk)


def apply_for_trainer(user, profile: TrainerProfile) -> TrainerProfile:
    """Save the trainer application and move the user to PENDING_APPLICATION."""
    with transaction.atomic():
        locked = _locked_user(user)
        locked.apply_transition(StatusTransition.APPLY)
        locked.save(update_fields=['status'])

        profile.user = locked
        profile.save()
    user.status = locked.status
    return profile


def approve_trainer(profile: TrainerProfile) -> TrainerProfile:
    """Approve a pending trainer application."""
    with transaction.atomic():
        user = _locked_user(profile.user)
        user.apply_transition(StatusTransition.APPROVE)
        user.save(update_fields=['status'])
    profile.user = user
    return profile


def ban_trainer(profile: TrainerProfile) -> TrainerProfile:
    """Suspend a trainer: deactivate the account so they can no longer log in."""
    with transaction.atomic():
        user = _locked_user(profile.user)
        user.apply_transition(StatusTransition.BAN)
        user.is_active = False
        user.save(update_fields=['is_active', 'status'])
    profile.user = user
    return profile


def unban_trainer(profile: TrainerProfile) -> TrainerProfile:
    """Restore a suspended trainer account."""
    with transaction.atomic():
        user = _locked_user(profile.user)
        user.apply_transition(StatusTransition.UNBAN)
        user.is_active = True
        user.save(update_fields=['is_active', 'status'])
    profile.user = user
    return profile


def apply_profile_content(source: TrainerProfileContent, target: TrainerProfileContent) -> None:
    """Copy every editable plain field from one profile-like object to another (in memory)."""
    for field_name in TrainerProfileContent.content_field_names():
        setattr(target, field_name, getattr(source, field_name))


def approve_profile_update(update_obj: TrainerProfileUpdate) -> TrainerProfile:
    """
    Service to approve a pending profile update.
    Applies the changes to the main TrainerProfile and deletes the pending update.
    """
    profile = update_obj.profile

    with transaction.atomic():
        apply_profile_content(update_obj, profile)
        profile.sports.set(update_obj.sports.all())

        if update_obj.profile_picture:
            # Duplicate the file so django-cleanup can safely delete the pending one
            profile.profile_picture.save(
                os.path.basename(update_obj.profile_picture.name),
                ContentFile(update_obj.profile_picture.read()),
                save=False
            )

        profile.save()

        # Remove the pending update request (django-cleanup will delete its file)
        update_obj.delete()

    return profile


def reject_profile_update(update_obj: TrainerProfileUpdate) -> None:
    """
    Service to reject a pending profile update and clean up any uploaded files.
    """
    # django-cleanup handles file deletion automatically
    update_obj.delete()
