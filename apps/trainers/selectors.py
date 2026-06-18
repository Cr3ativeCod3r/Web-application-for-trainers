from typing import Iterable, Set, Dict, Any, Tuple
from django.db.models import QuerySet, Q
from .models import TrainerProfile, TrainerProfileUpdate, TrainerPost
from apps.accounts.models import TrainerStatus

def get_approved_trainers() -> QuerySet[TrainerProfile]:
    """Returns a queryset of approved trainer profiles."""
    return TrainerProfile.objects.filter(user__status=TrainerStatus.APPROVED_TRAINER)

def search_trainers(sport: str = '', location: str = '', training_type: str = '') -> QuerySet[TrainerProfile]:
    """
    Search approved trainers based on sport, location, and training type.
    """
    trainers = get_approved_trainers()
    
    if sport:
        trainers = trainers.filter(sport__icontains=sport)
    if location:
        trainers = trainers.filter(location__icontains=location)
    if training_type in ['ONLINE', 'STATIONARY']:
        trainers = trainers.filter(Q(training_type=training_type) | Q(training_type='BOTH'))
        
    return trainers.order_by('-created_at')

def get_autocomplete_suggestions(q_type: str, query: str) -> list[str]:
    """
    Get autocomplete suggestions for sports or locations.
    """
    if not query or len(query) < 1:
        return []
        
    approved_profiles = get_approved_trainers()
    results: Set[str] = set()
    
    if q_type == 'sport':
        for profile in approved_profiles.filter(sport__icontains=query):
            for sport in profile.sports_list:
                if query in sport.lower():
                    results.add(sport)
    elif q_type == 'location':
        locations = approved_profiles.filter(location__icontains=query).values_list('location', flat=True).distinct()
        for loc in locations:
            results.add(loc)
            
    return sorted(list(results))[:10]

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
    pending_profiles = TrainerProfile.objects.filter(user__status=TrainerStatus.PENDING_APPLICATION)
    active_profiles = get_approved_trainers()
    banned_profiles = TrainerProfile.objects.filter(user__status=TrainerStatus.BANNED)
    pending_updates = TrainerProfileUpdate.objects.all()
    all_posts = TrainerPost.objects.all()

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
