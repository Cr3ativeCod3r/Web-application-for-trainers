"""
Signals are used (rather than calls in every service) because users and profiles
are also edited from the Django admin, allauth and management commands - any
missed code path would silently leave other services with stale data.
"""
from django.contrib.auth import get_user_model
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.trainers.models import TrainerProfile

from .integration_events import publish_user_deleted, publish_user_updated
from .models import ClientProfile

User = get_user_model()

# Saving only these fields does not change anything other services can see.
IRRELEVANT_USER_FIELDS = frozenset({'last_login', 'password'})


@receiver(post_save, sender=User, dispatch_uid='accounts_user_saved')
def user_saved(sender, instance, raw=False, update_fields=None, **kwargs):
    if raw:  # loaddata
        return
    if update_fields and set(update_fields) <= IRRELEVANT_USER_FIELDS:
        return
    publish_user_updated(instance.pk)


@receiver(post_delete, sender=User, dispatch_uid='accounts_user_deleted')
def user_deleted(sender, instance, **kwargs):
    publish_user_deleted(instance.pk)


@receiver(post_save, sender=TrainerProfile, dispatch_uid='accounts_trainer_profile_saved')
@receiver(post_save, sender=ClientProfile, dispatch_uid='accounts_client_profile_saved')
def profile_saved(sender, instance, raw=False, **kwargs):
    if not raw:
        publish_user_updated(instance.user_id)


@receiver(post_delete, sender=TrainerProfile, dispatch_uid='accounts_trainer_profile_deleted')
@receiver(post_delete, sender=ClientProfile, dispatch_uid='accounts_client_profile_deleted')
def profile_deleted(sender, instance, **kwargs):
    publish_user_updated(instance.user_id)
