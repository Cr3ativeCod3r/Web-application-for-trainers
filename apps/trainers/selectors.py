from typing import Set
from django.db.models import QuerySet, Q
from .models import TrainerProfile
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
        trainers = trainers.filter(sports__name__icontains=sport).distinct()
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
    
    if q_type == 'sport':
        from .models import Sport
        # Filter sports that are related to approved profiles and match query
        sports = Sport.objects.filter(
            name__icontains=query,
            trainers__in=approved_profiles
        ).values_list('name', flat=True).distinct()
        return list(sports)[:10]
        
    elif q_type == 'location':
        locations = approved_profiles.filter(location__icontains=query).values_list('location', flat=True).distinct()
        return list(locations)[:10]
            
    return []
