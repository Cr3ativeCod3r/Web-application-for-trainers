import os
from django.db import transaction
from .models import TrainerProfile, TrainerProfileUpdate
from apps.accounts.models import TrainerStatus

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

def approve_profile_update(update_obj: TrainerProfileUpdate) -> TrainerProfile:
    """
    Service to approve a pending profile update. 
    Applies the changes to the main TrainerProfile and deletes the pending update.
    """
    profile = update_obj.profile
    
    with transaction.atomic():
        # Copy fields from update object to the main profile
        profile.full_name = update_obj.full_name
        profile.sports.set(update_obj.sports.all())
        profile.location = update_obj.location
        profile.headline = update_obj.headline
        profile.description = update_obj.description
        profile.classes_description = update_obj.classes_description
        profile.hourly_rate = update_obj.hourly_rate
        profile.contact_email = update_obj.contact_email
        profile.contact_phone = update_obj.contact_phone
        
        # Handle profile picture replacement
        if update_obj.profile_picture:
            # Duplicate the file so django-cleanup can safely delete the pending one
            from django.core.files.base import ContentFile
            profile.profile_picture.save(
                os.path.basename(update_obj.profile_picture.name),
                ContentFile(update_obj.profile_picture.read()),
                save=False
            )
            
        profile.instagram = update_obj.instagram
        profile.facebook = update_obj.facebook
        profile.tiktok = update_obj.tiktok
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
