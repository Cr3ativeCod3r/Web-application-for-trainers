import os

from django.core.files.base import ContentFile
from django.db import transaction

from apps.accounts.models import TrainerStatus

from .models import TrainerProfile, TrainerProfileContent, TrainerProfileUpdate


def apply_for_trainer(user, profile: TrainerProfile) -> TrainerProfile:
    """
    Service to handle the logic when a user applies to become a trainer.
    Updates the user's status and saves the profile.
    """
    with transaction.atomic():
        profile.user = user
        profile.save()

        user.status = TrainerStatus.PENDING_APPLICATION
        user.save()
    return profile

def approve_trainer(profile: TrainerProfile) -> TrainerProfile:
    """
    Service to approve a trainer application.
    """
    with transaction.atomic():
        profile.user.status = TrainerStatus.APPROVED_TRAINER
        profile.user.save()
    return profile

def ban_trainer(profile: TrainerProfile) -> TrainerProfile:
    """Suspend a trainer: deactivate the account so they can no longer log in."""
    user = profile.user
    user.is_active = False
    user.status = TrainerStatus.BANNED
    user.save(update_fields=['is_active', 'status'])
    return profile

def unban_trainer(profile: TrainerProfile) -> TrainerProfile:
    """Restore a suspended trainer account."""
    user = profile.user
    user.is_active = True
    user.status = TrainerStatus.APPROVED_TRAINER
    user.save(update_fields=['is_active', 'status'])
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
