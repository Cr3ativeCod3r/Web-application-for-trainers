from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import TrainerProfile
from .forms import TrainerApplicationForm
from accounts.models import TrainerStatus

def home_search_view(request):
    """
    Mockup view for the home search page.
    """
    return render(request, 'trainers/home_search.html')

@login_required
def apply_trainer_view(request):
    # Only allow application if they haven't applied yet
    if request.user.status != TrainerStatus.REGISTERED:
        messages.info(request, "Twój wniosek został już złożony lub jesteś trenerem.")
        return redirect('trainers:home_search')

    if request.method == 'POST':
        form = TrainerApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()
            
            # Change status to pending
            request.user.status = TrainerStatus.PENDING_APPLICATION
            request.user.save()
            
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
            }
            form = TrainerProfileUpdateForm(initial=initial_data)

    return render(request, 'trainers/account.html', {'form': form, 'pending_update': pending_update, 'profile': profile})

@staff_member_required
def admin_dashboard_view(request):
    pending_profiles = TrainerProfile.objects.filter(user__status=TrainerStatus.PENDING_APPLICATION)
    active_profiles = TrainerProfile.objects.filter(user__status=TrainerStatus.APPROVED_TRAINER)
    pending_updates = TrainerProfileUpdate.objects.all()
    
    context = {
        'pending_profiles': pending_profiles,
        'active_profiles': active_profiles,
        'pending_updates': pending_updates,
    }
    return render(request, 'trainers/admin_dashboard.html', context)

@staff_member_required
def approve_trainer_view(request, profile_id):
    profile = TrainerProfile.objects.get(id=profile_id)
    profile.user.status = TrainerStatus.APPROVED_TRAINER
    profile.user.save()
    messages.success(request, f"Trener {profile.full_name} został zatwierdzony!")
    return redirect('trainers:admin_dashboard')

@staff_member_required
def approve_update_view(request, update_id):
    update_obj = TrainerProfileUpdate.objects.get(id=update_id)
    profile = update_obj.profile
    # Kopiuj pola
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
        # Usuń stare zdjęcie profilowe z dysku, jeśli wgrywane jest nowe
        import os
        if profile.profile_picture and profile.profile_picture != update_obj.profile_picture:
            if os.path.isfile(profile.profile_picture.path):
                try:
                    os.remove(profile.profile_picture.path)
                except Exception:
                    pass
        profile.profile_picture = update_obj.profile_picture
    profile.instagram = update_obj.instagram
    profile.facebook = update_obj.facebook
    profile.tiktok = update_obj.tiktok
    profile.save()
    update_obj.delete()
    messages.success(request, f"Zmiany w profilu {profile.full_name} zostały zatwierdzone.")
    return redirect('trainers:admin_dashboard')

@staff_member_required
def reject_update_view(request, update_id):
    update_obj = TrainerProfileUpdate.objects.get(id=update_id)
    profile_name = update_obj.profile.full_name
    
    # Jeśli odrzucamy, to usuwamy wgrany przez usera plik do aktualizacji (jeśli istnieje)
    if update_obj.profile_picture:
        import os
        if os.path.isfile(update_obj.profile_picture.path):
            try:
                os.remove(update_obj.profile_picture.path)
            except Exception:
                pass
                
    update_obj.delete()
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
    
    # Podmiana danych w pamięci do podglądu (nie zapisujemy)
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
            
            # Usunięcie zdjęć z dysku
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
