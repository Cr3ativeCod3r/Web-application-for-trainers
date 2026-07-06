from django.urls import path
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from . import views
from .forms import SinglePasswordSetForm

from django.conf import settings

app_name = 'accounts'

urlpatterns = [
    path('logowanie/', views.ClientLoginView.as_view(), name='login'),
    path('rejestracja/', views.ClientRegisterView.as_view(), name='register'),
    path('wyloguj/', auth_views.LogoutView.as_view(), name='logout'),
    
    path('zapomnialem-hasla/', auth_views.PasswordResetView.as_view(
        template_name='accounts/password_reset.html',
        email_template_name='emails/clients/password_reset.txt',
        html_email_template_name='emails/clients/password_reset.html',
        success_url='/zapomnialem-hasla/wyslano/',
        extra_email_context={'domain': settings.DOMAIN, 'site_name': 'Coachly'}
    ), name='password_reset'),
    
    path('zapomnialem-hasla/wyslano/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html'
    ), name='password_reset_done'),
    
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html',
        form_class=SinglePasswordSetForm,
        success_url='/reset/zakonczono/'
    ), name='password_reset_confirm'),
    
    path('reset/zakonczono/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html'
    ), name='password_reset_complete'),

    # Email Activation
    path('aktywacja/<uidb64>/<token>/', views.ActivateAccountView.as_view(), name='activate'),
    
    # Chat
    path('wiadomosci/', views.ChatView.as_view(), name='chat'),
    path('api/user-info/<int:user_id>/', views.user_info_api, name='user_info_api'),
]
