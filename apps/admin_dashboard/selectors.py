from typing import Dict
from django.db.models import QuerySet

from apps.trainers.models import TrainerProfile, TrainerProfileUpdate, TrainerPost
from apps.trainers.selectors import get_approved_trainers
from apps.accounts.models import TrainerStatus


def get_admin_dashboard_data(
    q_pending: str = '',
    q_active: str = '',
    q_updates: str = '',
    q_banned: str = '',
    q_posts: str = ''
) -> Dict[str, QuerySet]:
    """
    Returns querysets needed for the admin dashboard, optionally filtered.
    """
    pending_profiles = TrainerProfile.objects.filter(user__status=TrainerStatus.PENDING_APPLICATION).select_related('user').prefetch_related('sports')
    active_profiles = get_approved_trainers()
    banned_profiles = TrainerProfile.objects.filter(user__status=TrainerStatus.BANNED).select_related('user').prefetch_related('sports')
    pending_updates = TrainerProfileUpdate.objects.all().select_related('profile', 'profile__user').prefetch_related('sports')
    all_posts = TrainerPost.objects.all().select_related('trainer', 'trainer__user')

    if q_pending:
        pending_profiles = pending_profiles.filter(contact_email__icontains=q_pending)
    if q_active:
        active_profiles = active_profiles.filter(contact_email__icontains=q_active)
    if q_updates:
        pending_updates = pending_updates.filter(profile__contact_email__icontains=q_updates)
    if q_banned:
        banned_profiles = banned_profiles.filter(contact_email__icontains=q_banned)
    if q_posts:
        all_posts = all_posts.filter(title__icontains=q_posts)

    return {
        'pending_profiles': pending_profiles.order_by('-created_at'),
        'active_profiles': active_profiles.order_by('-created_at'),
        'pending_updates': pending_updates.order_by('-created_at'),
        'banned_profiles': banned_profiles.order_by('-created_at'),
        'all_posts': all_posts.order_by('-created_at'),
    }
