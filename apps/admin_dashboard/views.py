from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.trainers import services
from apps.trainers.models import TrainerPost, TrainerProfile, TrainerProfileUpdate

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
@require_POST
def approve_trainer_view(request, profile_id):
    """Approve a pending trainer application."""
    profile = get_object_or_404(TrainerProfile, id=profile_id)
    services.approve_trainer(profile)
    messages.success(request, f"Trener {profile.full_name} został zatwierdzony!")
    return redirect('admin_dashboard:dashboard')


@staff_member_required
@require_POST
def approve_update_view(request, update_id):
    """Approve a pending profile update request."""
    update_obj = get_object_or_404(TrainerProfileUpdate, id=update_id)
    profile = services.approve_profile_update(update_obj)
    messages.success(request, f"Zmiany w profilu {profile.full_name} zostały zatwierdzone.")
    return redirect('admin_dashboard:dashboard')


@staff_member_required
@require_POST
def reject_update_view(request, update_id):
    """Reject a pending profile update request."""
    update_obj = get_object_or_404(TrainerProfileUpdate, id=update_id)
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
    services.apply_profile_content(update_obj, profile)
    profile._prefetched_objects_cache = {'sports': list(update_obj.sports.all())}
    if update_obj.profile_picture:
        profile.profile_picture = update_obj.profile_picture

    return render(request, 'trainers/public_profile.html', {'profile': profile, 'is_preview': True})


superuser_required = user_passes_test(lambda u: u.is_active and u.is_superuser)


@login_required
@superuser_required
@require_POST
def ban_trainer_view(request, profile_id):
    """Ban a trainer account."""
    profile = get_object_or_404(TrainerProfile, id=profile_id)
    services.ban_trainer(profile)
    messages.success(request, f"Konto trenera {profile.full_name} zostało zawieszone.")
    return redirect(reverse('admin_dashboard:dashboard') + '?tab=active')


@login_required
@superuser_required
@require_POST
def unban_trainer_view(request, profile_id):
    """Unban a trainer account."""
    profile = get_object_or_404(TrainerProfile, id=profile_id)
    services.unban_trainer(profile)
    messages.success(request, f"Konto trenera {profile.full_name} zostało odwieszone.")
    return redirect(reverse('admin_dashboard:dashboard') + '?tab=active')


@login_required
@superuser_required
@require_POST
def delete_trainer_view(request, profile_id):
    """Permanently delete a trainer account."""
    profile = get_object_or_404(TrainerProfile, id=profile_id)
    full_name = profile.full_name
    profile.user.delete()
    messages.success(request, f"Konto trenera {full_name} zostało trwale usunięte.")
    return redirect(reverse('admin_dashboard:dashboard') + '?tab=active')


@login_required
@superuser_required
@require_POST
def admin_delete_post_view(request, post_id):
    """Delete a trainer post from the admin dashboard."""
    post = get_object_or_404(TrainerPost, id=post_id)
    title = post.title
    post.delete()
    messages.success(request, f"Post '{title}' został usunięty.")
    return redirect(reverse('admin_dashboard:dashboard') + '?tab=posts')
