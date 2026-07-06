from django.urls import path
from django.contrib.auth import views as auth_views
from django.conf import settings
from . import views

app_name = 'trainers'

urlpatterns = [
    path('', views.home_search_view, name='home_search'),
    path('api/autocomplete/', views.autocomplete_view, name='autocomplete'),
    path('aplikuj/', views.apply_trainer_view, name='apply'),
    path('moje-konto/', views.trainer_account_view, name='account'),
    path('moje-konto/publikacje/', views.post_list_view, name='post_list'),
    path('moje-konto/publikacje/dodaj/', views.post_create_view, name='post_create'),
    path('moje-konto/publikacje/edytuj/<int:post_id>/', views.post_edit_view, name='post_edit'),
    path('moje-konto/publikacje/usun/<int:post_id>/', views.post_delete_view, name='post_delete'),
    path('usun-konto/', views.delete_account_view, name='delete_account'),

    # Auth routes must come BEFORE the wildcard <slug:username>/ pattern
    path('trenerzy/', views.TrainerLoginView.as_view(), name='login'),
    path('trenerzy/rejestracja/', views.TrainerRegisterView.as_view(), name='register'),
    path('trenerzy/rejestracja/sukces/', views.RegistrationSuccessView.as_view(), name='registration_success'),
    path('trenerzy/zapomnialem-hasla/', auth_views.PasswordResetView.as_view(
        template_name='accounts/password_reset.html',
        email_template_name='emails/trainers/password_reset.txt',
        html_email_template_name='emails/trainers/password_reset.html',
        success_url='/trenerzy/zapomnialem-hasla/wyslano/',
        extra_email_context={'domain': settings.DOMAIN, 'site_name': 'Coachly'}
    ), name='trainer_password_reset'),
    path('trenerzy/zapomnialem-hasla/wyslano/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html'
    ), name='trainer_password_reset_done'),

    path('<slug:username>/', views.public_profile_view, name='public_profile'),
    path('<slug:username>/<slug:slug>/', views.public_post_view, name='public_post'),
]
