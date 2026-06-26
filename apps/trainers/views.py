from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import TrainerProfile
from .forms import TrainerApplicationForm
from apps.accounts.models import TrainerStatus

from django.http import JsonResponse

from . import selectors
from . import services

from django_ratelimit.decorators import ratelimit
from django.core.paginator import Paginator
from django.contrib.auth import logout
from .forms import TrainerProfileUpdateForm, TrainerPostForm
from .models import TrainerProfileUpdate, TrainerPost
import os
def home_search_view(request):
    """
    View for the home search page with filtering capabilities.
    """
    query_sport = request.GET.get('sport', '').strip()
    query_location = request.GET.get('location', '').strip()
    query_type = request.GET.get('type', '').strip()
    
    # Use selector to fetch trainers
    trainers = selectors.search_trainers(query_sport, query_location, query_type)
    
    paginator = Paginator(trainers, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'trainers/home_search.html', {
        'trainers': page_obj,
        'query_sport': query_sport,
        'query_location': query_location,
        'query_type': query_type
    })

def autocomplete_view(request):
    """
    Returns JSON suggestions for sports and locations.
    """
    q_type = request.GET.get('type', '')
    q = request.GET.get('q', '').strip().lower()
    
    # Use selector for autocomplete
    results = selectors.get_autocomplete_suggestions(q_type, q)
            
    return JsonResponse({'results': results})


@login_required
@ratelimit(key='user', rate='5/m', block=True)
def apply_trainer_view(request):
    # Only allow application if they haven't applied yet
    if request.user.status != TrainerStatus.REGISTERED:
        messages.info(request, "Twój wniosek został już złożony lub jesteś trenerem.")
        return redirect('trainers:home_search')

    if request.method == 'POST':
        form = TrainerApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            profile = form.save(commit=False)
            
            # Use service to apply
            services.apply_for_trainer(request.user, profile)
            form.save_m2m()
            
            messages.success(request, "Twój wniosek został wysłany. Oczekuj na weryfikację!")
            return redirect('trainers:home_search')
    else:
        form = TrainerApplicationForm()

    return render(request, 'trainers/apply.html', {'form': form})



def public_profile_view(request, username):
    profile = get_object_or_404(TrainerProfile, username=username, user__status=TrainerStatus.APPROVED_TRAINER)
    return render(request, 'trainers/public_profile.html', {'profile': profile})

@login_required
@ratelimit(key='user', rate='10/m', block=True)
def trainer_account_view(request):
    try:
        profile = request.user.trainer_profile
    except TrainerProfile.DoesNotExist:
        messages.error(request, "Nie masz jeszcze profilu trenera.")
        return redirect('trainers:apply')
    
    pending_update = getattr(profile, 'pending_update', None)
    
    if request.method == 'POST':
        form = TrainerProfileUpdateForm(request.POST, request.FILES, instance=pending_update)
        if form.is_valid():
            # The old image deletion is now handled automatically by django-cleanup.
            update_obj = form.save(commit=False)
            update_obj.profile = profile
            update_obj.save()
            form.save_m2m()
            messages.success(request, "Twoje zmiany zostały zapisane i oczekują na akceptację administratora.")
            return redirect('trainers:account')
    else:
        # Pre-fill with pending_update if exists, otherwise profile
        if pending_update:
            form = TrainerProfileUpdateForm(instance=pending_update)
        else:
            # We need to create an instance-like dictionary or just use initial
            initial_data = {
                'full_name': profile.full_name,
                'sports': profile.sports.all(),
                'location': profile.location,
                'headline': profile.headline,
                'description': profile.description,
                'classes_description': profile.classes_description,
                'hourly_rate': profile.hourly_rate,
                'contact_email': profile.contact_email,
                'contact_phone': profile.contact_phone,
                'profile_picture': profile.profile_picture,
                'instagram': profile.instagram,
                'facebook': profile.facebook,
                'tiktok': profile.tiktok,
                'gender': profile.gender,
                'training_type': profile.training_type,
            }
            form = TrainerProfileUpdateForm(initial=initial_data)

    return render(request, 'trainers/account.html', {'form': form, 'pending_update': pending_update, 'profile': profile})



@login_required
def delete_account_view(request):
    if request.method == 'POST':
        password = request.POST.get('password')
        if request.user.check_password(password):
            user = request.user
            # The image deletion is now handled automatically by django-cleanup upon user.delete() cascading.
                
            logout(request)
            user.delete()
            messages.success(request, "Twoje konto wraz ze wszystkimi danymi zostało trwale usunięte.")
            return redirect('accounts:login')
        else:
            messages.error(request, "Podane hasło jest nieprawidłowe. Konto nie zostało usunięte.")
    return redirect('trainers:account')



@login_required
def post_list_view(request):
    try:
        profile = request.user.trainer_profile
    except TrainerProfile.DoesNotExist:
        messages.error(request, "Nie masz jeszcze profilu trenera.")
        return redirect('trainers:apply')
        
    posts = TrainerPost.objects.filter(trainer=profile).order_by('-created_at')
    
    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'trainers/post_list.html', {'posts': page_obj})

@login_required
@ratelimit(key='user', rate='10/m', block=True)
def post_create_view(request):
    try:
        profile = request.user.trainer_profile
    except TrainerProfile.DoesNotExist:
        messages.error(request, "Nie masz jeszcze profilu trenera.")
        return redirect('trainers:apply')
        
    if request.method == 'POST':
        form = TrainerPostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.trainer = profile
            post.save()
            messages.success(request, "Post został pomyślnie dodany.")
            return redirect('trainers:post_list')
    else:
        form = TrainerPostForm()
        
    return render(request, 'trainers/post_form.html', {'form': form, 'title': 'Dodaj nowy post'})

@login_required
def post_edit_view(request, post_id):
    try:
        profile = request.user.trainer_profile
    except TrainerProfile.DoesNotExist:
        messages.error(request, "Nie masz profilu trenera.")
        return redirect('trainers:apply')
        
    post = get_object_or_404(TrainerPost, id=post_id, trainer=profile)
    
    if request.method == 'POST':
        form = TrainerPostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, "Post został pomyślnie zaktualizowany.")
            return redirect('trainers:post_list')
    else:
        form = TrainerPostForm(instance=post)
        
    return render(request, 'trainers/post_form.html', {'form': form, 'title': 'Edytuj post', 'post': post})

@login_required
def post_delete_view(request, post_id):
    try:
        profile = request.user.trainer_profile
    except TrainerProfile.DoesNotExist:
        messages.error(request, "Nie masz profilu trenera.")
        return redirect('trainers:apply')
        
    post = get_object_or_404(TrainerPost, id=post_id, trainer=profile)
    
    if request.method == 'POST':
        post.delete()
        messages.success(request, "Post został pomyślnie usunięty.")
        
    return redirect('trainers:post_list')

def public_post_view(request, username, slug):
    profile = get_object_or_404(TrainerProfile, username=username, user__status=TrainerStatus.APPROVED_TRAINER)
    post = get_object_or_404(TrainerPost, trainer=profile, slug=slug)
    
    return render(request, 'trainers/public_post.html', {'profile': profile, 'post': post})
