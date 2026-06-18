from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import TrainerProfile
from .forms import TrainerApplicationForm
from apps.accounts.models import TrainerStatus

from django.db.models import Q
from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings

from . import selectors
from . import services

def home_search_view(request):
    """
    View for the home search page with filtering capabilities.
    """
    query_sport = request.GET.get('sport', '').strip()
    query_location = request.GET.get('location', '').strip()
    query_type = request.GET.get('type', '').strip()
    
    # Use selector to fetch trainers
    trainers = selectors.search_trainers(query_sport, query_location, query_type)
    
    from django.core.paginator import Paginator
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

from django_ratelimit.decorators import ratelimit

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
            
            messages.success(request, "Twój wniosek został wysłany. Oczekuj na weryfikację!")
            return redirect('trainers:home_search')
    else:
        form = TrainerApplicationForm()

    return render(request, 'trainers/apply.html', {'form': form})

from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404
from .forms import TrainerApplicationForm, TrainerProfileUpdateForm
from .models import TrainerProfile, TrainerProfileUpdate

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
            # Delete old pending picture if a new one is uploaded
            if 'profile_picture' in request.FILES and pending_update and pending_update.profile_picture:
                import os
                if os.path.isfile(pending_update.profile_picture.path):
                    try:
                        os.remove(pending_update.profile_picture.path)
                    except Exception:
                        pass
                        
            update_obj = form.save(commit=False)
            update_obj.profile = profile
            update_obj.save()
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
                'sport': profile.sport,
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

from django.core.paginator import Paginator

@staff_member_required
def admin_dashboard_view(request):
    q_pending = request.GET.get('q_pending', '').strip()
    q_active = request.GET.get('q_active', '').strip()
    q_updates = request.GET.get('q_updates', '').strip()
    q_banned = request.GET.get('q_banned', '').strip()
    q_posts = request.GET.get('q_posts', '').strip()

    # Use selector to get dashboard data
    dashboard_data = selectors.get_admin_dashboard_data(
        q_pending, q_active, q_updates, q_banned, q_posts
    )

    paginator_pending = Paginator(dashboard_data['pending_profiles'], 12)
    paginator_active = Paginator(dashboard_data['active_profiles'], 12)
    paginator_updates = Paginator(dashboard_data['pending_updates'], 12)
    paginator_banned = Paginator(dashboard_data['banned_profiles'], 12)
    paginator_posts = Paginator(dashboard_data['all_posts'], 12)

    page_pending = request.GET.get('p_pending')
    page_active = request.GET.get('p_active')
    page_updates = request.GET.get('p_updates')
    page_banned = request.GET.get('p_banned')
    page_posts = request.GET.get('p_posts')

    context = {
        'pending_profiles': paginator_pending.get_page(page_pending),
        'active_profiles': paginator_active.get_page(page_active),
        'pending_updates': paginator_updates.get_page(page_updates),
        'banned_profiles': paginator_banned.get_page(page_banned),
        'all_posts': paginator_posts.get_page(page_posts),
        'q_pending': q_pending,
        'q_active': q_active,
        'q_updates': q_updates,
        'q_banned': q_banned,
        'q_posts': q_posts,
    }
    return render(request, 'trainers/admin_dashboard.html', context)

@staff_member_required
def approve_trainer_view(request, profile_id):
    profile = TrainerProfile.objects.get(id=profile_id)
    # Use service to approve trainer
    services.approve_trainer(profile)
    messages.success(request, f"Trener {profile.full_name} został zatwierdzony!")
    return redirect('trainers:admin_dashboard')

@staff_member_required
def approve_update_view(request, update_id):
    update_obj = TrainerProfileUpdate.objects.get(id=update_id)
    # Use service to approve update
    profile = services.approve_profile_update(update_obj)
    messages.success(request, f"Zmiany w profilu {profile.full_name} zostały zatwierdzone.")
    return redirect('trainers:admin_dashboard')

@staff_member_required
def reject_update_view(request, update_id):
    update_obj = TrainerProfileUpdate.objects.get(id=update_id)
    profile_name = update_obj.profile.full_name
    
    # Use service to reject update
    services.reject_profile_update(update_obj)
    
    messages.warning(request, f"Zmiany w profilu {profile_name} zostały odrzucone.")
    return redirect('trainers:admin_dashboard')

@staff_member_required
def admin_profile_preview_view(request, profile_id):
    profile = get_object_or_404(TrainerProfile, id=profile_id)
    return render(request, 'trainers/public_profile.html', {'profile': profile, 'is_preview': True})

@staff_member_required
def admin_update_preview_view(request, update_id):
    update_obj = get_object_or_404(TrainerProfileUpdate, id=update_id)
    profile = update_obj.profile
    
    # Swap data in memory for preview (do not save)
    profile.full_name = update_obj.full_name
    profile.sport = update_obj.sport
    profile.location = update_obj.location
    profile.headline = update_obj.headline
    profile.description = update_obj.description
    profile.classes_description = update_obj.classes_description
    profile.hourly_rate = update_obj.hourly_rate
    profile.contact_email = update_obj.contact_email
    profile.contact_phone = update_obj.contact_phone
    if update_obj.profile_picture:
        profile.profile_picture = update_obj.profile_picture
    profile.instagram = update_obj.instagram
    profile.facebook = update_obj.facebook
    profile.tiktok = update_obj.tiktok
    
    return render(request, 'trainers/public_profile.html', {'profile': profile, 'is_preview': True})

from django.contrib.auth import logout

@login_required
def delete_account_view(request):
    if request.method == 'POST':
        password = request.POST.get('password')
        if request.user.check_password(password):
            user = request.user
            
            # Delete images from disk
            import os
            try:
                if hasattr(user, 'trainer_profile'):
                    profile = user.trainer_profile
                    if profile.profile_picture and os.path.isfile(profile.profile_picture.path):
                        os.remove(profile.profile_picture.path)
                    if hasattr(profile, 'pending_update') and profile.pending_update.profile_picture:
                        if os.path.isfile(profile.pending_update.profile_picture.path):
                            os.remove(profile.pending_update.profile_picture.path)
            except Exception:
                pass
                
            logout(request)
            user.delete()
            messages.success(request, "Twoje konto wraz ze wszystkimi danymi zostało trwale usunięte.")
            return redirect('accounts:login')
        else:
            messages.error(request, "Podane hasło jest nieprawidłowe. Konto nie zostało usunięte.")
    return redirect('trainers:account')


@login_required
@user_passes_test(lambda u: u.is_superuser)
def ban_trainer_view(request, profile_id):
    if request.method == 'POST':
        profile = get_object_or_404(TrainerProfile, id=profile_id)
        user = profile.user
        user.is_active = False
        user.status = 'BANNED'
        user.save()
        messages.success(request, f"Konto trenera {profile.full_name} zostało zawieszone.")
    return redirect(reverse('trainers:admin_dashboard') + '?tab=active')

@login_required
@user_passes_test(lambda u: u.is_superuser)
def delete_trainer_view(request, profile_id):
    if request.method == 'POST':
        profile = get_object_or_404(TrainerProfile, id=profile_id)
        full_name = profile.full_name
        user = profile.user
        user.delete()
        messages.success(request, f"Konto trenera {full_name} zostało trwale usunięte.")
    return redirect(reverse('trainers:admin_dashboard') + '?tab=active')

@login_required
@user_passes_test(lambda u: u.is_superuser)
def unban_trainer_view(request, profile_id):
    if request.method == 'POST':
        profile = get_object_or_404(TrainerProfile, id=profile_id)
        user = profile.user
        user.is_active = True
        user.status = 'APPROVED_TRAINER'
        user.save()
        messages.success(request, f"Konto trenera {profile.full_name} zostało odwieszone.")
    return redirect(reverse('trainers:admin_dashboard') + '?tab=active')

from .models import TrainerPost
from .forms import TrainerPostForm
from django.utils.text import slugify

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

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_delete_post_view(request, post_id):
    if request.method == 'POST':
        post = get_object_or_404(TrainerPost, id=post_id)
        title = post.title
        post.delete()
        messages.success(request, f"Post '{title}' został usunięty.")
    return redirect(reverse('trainers:admin_dashboard') + '?tab=posts')

