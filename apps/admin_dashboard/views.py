from django.shortcuts import redirect, get_object_or_404
from django.shortcuts import render
from django.urls import reverse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.core.paginator import Paginator

from apps.trainers.models import TrainerProfile, TrainerProfileUpdate, TrainerPost
from apps.trainers import services
from . import selectors


@staff_member_required
def admin_dashboard_view(request):
    """Main admin dashboard view with tabbed interface for managing trainers."""
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
    return render(request, 'admin_dashboard/dashboard.html', context)


@staff_member_required
def approve_trainer_view(request, profile_id):
    """Approve a pending trainer application."""
    profile = TrainerProfile.objects.get(id=profile_id)
    services.approve_trainer(profile)
    messages.success(request, f"Trener {profile.full_name} został zatwierdzony!")
    return redirect('admin_dashboard:dashboard')


@staff_member_required
def approve_update_view(request, update_id):
    """Approve a pending profile update request."""
    update_obj = TrainerProfileUpdate.objects.get(id=update_id)
    profile = services.approve_profile_update(update_obj)
    messages.success(request, f"Zmiany w profilu {profile.full_name} zostały zatwierdzone.")
    return redirect('admin_dashboard:dashboard')


@staff_member_required
def reject_update_view(request, update_id):
    """Reject a pending profile update request."""
    update_obj = TrainerProfileUpdate.objects.get(id=update_id)
    profile_name = update_obj.profile.full_name
    services.reject_profile_update(update_obj)
    messages.warning(request, f"Zmiany w profilu {profile_name} zostały odrzucone.")
    return redirect('admin_dashboard:dashboard')


@staff_member_required
def admin_profile_preview_view(request, profile_id):
    """Preview a trainer profile (for pending applications)."""
    profile = get_object_or_404(TrainerProfile, id=profile_id)
    return render(request, 'trainers/public_profile.html', {'profile': profile, 'is_preview': True})


@staff_member_required
def admin_update_preview_view(request, update_id):
    """Preview how a profile would look after applying pending changes."""
    update_obj = get_object_or_404(TrainerProfileUpdate, id=update_id)
    profile = update_obj.profile

    # Swap data in memory for preview (do not save)
    profile.full_name = update_obj.full_name
    profile._prefetched_objects_cache = {'sports': list(update_obj.sports.all())}
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
    profile.tags = update_obj.tags

    return render(request, 'trainers/public_profile.html', {'profile': profile, 'is_preview': True})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def ban_trainer_view(request, profile_id):
    """Ban a trainer account."""
    if request.method == 'POST':
        profile = get_object_or_404(TrainerProfile, id=profile_id)
        user = profile.user
        user.is_active = False
        user.status = 'BANNED'
        user.save()
        messages.success(request, f"Konto trenera {profile.full_name} zostało zawieszone.")
    return redirect(reverse('admin_dashboard:dashboard') + '?tab=active')


@login_required
@user_passes_test(lambda u: u.is_superuser)
def unban_trainer_view(request, profile_id):
    """Unban a trainer account."""
    if request.method == 'POST':
        profile = get_object_or_404(TrainerProfile, id=profile_id)
        user = profile.user
        user.is_active = True
        user.status = 'APPROVED_TRAINER'
        user.save()
        messages.success(request, f"Konto trenera {profile.full_name} zostało odwieszone.")
    return redirect(reverse('admin_dashboard:dashboard') + '?tab=active')


@login_required
@user_passes_test(lambda u: u.is_superuser)
def delete_trainer_view(request, profile_id):
    """Permanently delete a trainer account."""
    if request.method == 'POST':
        profile = get_object_or_404(TrainerProfile, id=profile_id)
        full_name = profile.full_name
        user = profile.user
        user.delete()
        messages.success(request, f"Konto trenera {full_name} zostało trwale usunięte.")
    return redirect(reverse('admin_dashboard:dashboard') + '?tab=active')


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_delete_post_view(request, post_id):
    """Delete a trainer post from the admin dashboard."""
    if request.method == 'POST':
        post = get_object_or_404(TrainerPost, id=post_id)
        title = post.title
        post.delete()
        messages.success(request, f"Post '{title}' został usunięty.")
    return redirect(reverse('admin_dashboard:dashboard') + '?tab=posts')
