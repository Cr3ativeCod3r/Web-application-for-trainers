from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .forms import SinglePasswordSetForm

app_name = 'accounts'

urlpatterns = [
    # Auth
    path('', views.TrainerLoginView.as_view(), name='login'),
    path('rejestracja/', views.TrainerRegisterView.as_view(), name='register'),
    path('wyloguj/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Password Reset
    path('zapomnialem-hasla/', auth_views.PasswordResetView.as_view(
        template_name='accounts/password_reset.html',
        email_template_name='accounts/password_reset_email.html',
        success_url='/trenerzy/zapomnialem-hasla/wyslano/'
    ), name='password_reset'),
    path('zapomnialem-hasla/wyslano/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html'
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html',
        form_class=SinglePasswordSetForm,
        success_url='/trenerzy/reset/zakonczono/'
    ), name='password_reset_confirm'),
    path('reset/zakonczono/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html'
    ), name='password_reset_complete'),

    # Email Activation
    path('aktywacja/<uidb64>/<token>/', views.ActivateAccountView.as_view(), name='activate'),
]
