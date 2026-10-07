from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from apps.accounts.models import TrainerStatus

from . import selectors, services
from .forms import TrainerApplicationForm, TrainerPostForm, TrainerProfileUpdateForm
from .models import TrainerPost, TrainerProfile, TrainerProfileContent


def trainer_profile_required(view_func):
    """
    Requires a logged-in user with a trainer profile and passes it to the view
    as `profile`; users without one are sent to the application form.
    """
    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        profile = getattr(request.user, 'trainer_profile', None)
        if profile is None:
            messages.error(request, "Nie masz jeszcze profilu trenera.")
            return redirect('trainers:apply')
        return view_func(request, *args, profile=profile, **kwargs)
    return wrapper


# --- Public ----------------------------------------------------------------

def home_search_view(request):
    """Home page with trainer search and filters."""
    query_sport = request.GET.get('sport', '').strip()
    query_location = request.GET.get('location', '').strip()
    query_type = request.GET.get('type', '').strip()

    trainers = selectors.search_trainers(query_sport, query_location, query_type)
    page_obj = Paginator(trainers, 12).get_page(request.GET.get('page'))

    return render(request, 'trainers/home_search.html', {
        'trainers': page_obj,
        'query_sport': query_sport,
        'query_location': query_location,
        'query_type': query_type,
    })


def autocomplete_view(request):
    """Returns JSON suggestions for sports and locations."""
    q_type = request.GET.get('type', '')
    q = request.GET.get('q', '').strip().lower()
    return JsonResponse({'results': selectors.get_autocomplete_suggestions(q_type, q)})


def public_profile_view(request, username):
    profile = get_object_or_404(TrainerProfile, username=username, user__status=TrainerStatus.APPROVED_TRAINER)
    context = {
        'profile': profile,
        'chat_api_url': settings.CHAT_API_URL,
    }
    return render(request, 'trainers/public_profile.html', context)


def public_post_view(request, username, slug):
    profile = get_object_or_404(TrainerProfile, username=username, user__status=TrainerStatus.APPROVED_TRAINER)
    post = get_object_or_404(TrainerPost, trainer=profile, slug=slug)
    return render(request, 'trainers/public_post.html', {'profile': profile, 'post': post})


# --- Trainer application & account ---------------------------------------

@login_required
@ratelimit(key='user', rate='5/m', method='POST', block=True)
def apply_trainer_view(request):
    # Only allow application if they haven't applied yet
    if request.user.status != TrainerStatus.REGISTERED:
        messages.info(request, "Twój wniosek został już złożony lub jesteś trenerem.")
        return redirect('trainers:home_search')

    if request.method == 'POST':
        form = TrainerApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            profile = form.save(commit=False)
            services.apply_for_trainer(request.user, profile)
            form.save_m2m()
            messages.success(request, "Twój wniosek został wysłany. Oczekuj na weryfikację!")
            return redirect('trainers:home_search')
    else:
        form = TrainerApplicationForm()

    return render(request, 'trainers/apply.html', {'form': form})


@trainer_profile_required
@ratelimit(key='user', rate='10/m', method='POST', block=True)
def trainer_account_view(request, profile):
    pending_update = getattr(profile, 'pending_update', None)

    if request.method == 'POST':
        form = TrainerProfileUpdateForm(request.POST, request.FILES, instance=pending_update)
        if form.is_valid():
            # Replaced images are removed automatically by django-cleanup.
            update_obj = form.save(commit=False)
            update_obj.profile = profile
            update_obj.save()
            form.save_m2m()
            messages.success(request, "Twoje zmiany zostały zapisane i oczekują na akceptację administratora.")
            return redirect('trainers:account')
    elif pending_update:
        form = TrainerProfileUpdateForm(instance=pending_update)
    else:
        # No pending update yet: start the form from the live profile values
        initial_data = {name: getattr(profile, name) for name in TrainerProfileContent.content_field_names()}
        initial_data['sports'] = profile.sports.all()
        initial_data['profile_picture'] = profile.profile_picture
        form = TrainerProfileUpdateForm(initial=initial_data)

    return render(request, 'trainers/account.html', {'form': form, 'pending_update': pending_update, 'profile': profile})


@login_required
@require_POST
def delete_account_view(request):
    if not request.user.check_password(request.POST.get('password')):
        messages.error(request, "Podane hasło jest nieprawidłowe. Konto nie zostało usunięte.")
        return redirect('trainers:account')

    user = request.user
    logout(request)
    # Related profile, posts and images are removed by CASCADE + django-cleanup.
    user.delete()
    messages.success(request, "Twoje konto wraz ze wszystkimi danymi zostało trwale usunięte.")
    return redirect('accounts:login')


# --- Trainer posts ---------------------------------------------------------

@trainer_profile_required
def post_list_view(request, profile):
    posts = TrainerPost.objects.filter(trainer=profile).order_by('-created_at')
    page_obj = Paginator(posts, 10).get_page(request.GET.get('page'))
    return render(request, 'trainers/post_list.html', {'posts': page_obj})


@trainer_profile_required
@ratelimit(key='user', rate='10/m', method='POST', block=True)
def post_create_view(request, profile):
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


@trainer_profile_required
def post_edit_view(request, post_id, profile):
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


@trainer_profile_required
@require_POST
def post_delete_view(request, post_id, profile):
    post = get_object_or_404(TrainerPost, id=post_id, trainer=profile)
    post.delete()
    messages.success(request, "Post został pomyślnie usunięty.")
    return redirect('trainers:post_list')
