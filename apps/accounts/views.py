from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.contrib.auth.views import LoginView
from django.views.generic.edit import CreateView
from django.views.generic import View
from django.contrib import messages
from django.core.mail import send_mail
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.template.loader import render_to_string
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth import get_user_model

from .forms import TrainerRegistrationForm, CustomAuthenticationForm
from .tasks import send_activation_email_task

User = get_user_model()

class TrainerLoginView(LoginView):
    template_name = 'accounts/login.html'
    form_class = CustomAuthenticationForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        remember_me = form.cleaned_data.get('remember_me')
        if not remember_me:
            self.request.session.set_expiry(0)
            self.request.session.modified = True
        else:
            self.request.session.set_expiry(1209600)
            self.request.session.modified = True
        return super().form_valid(form)

from django.views.generic import View, TemplateView

class TrainerRegisterView(CreateView):
    template_name = 'accounts/register.html'
    form_class = TrainerRegistrationForm
    success_url = reverse_lazy('accounts:registration_success')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('trainers:home_search')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save(commit=False)
        user.is_active = False # Require email confirmation
        user.save()
        
        domain = self.request.get_host()
        
        # Zlecenie wysyłki e-maila w tle (Celery)
        send_activation_email_task.delay(user.pk, domain)
        
        return redirect(self.success_url)

class RegistrationSuccessView(TemplateView):
    template_name = 'accounts/registration_success.html'

class ActivateAccountView(View):
    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            user.is_active = True
            user.save()
            messages.success(request, 'Twoje konto zostało aktywowane. Możesz się teraz zalogować.')
            return redirect('accounts:login')
        else:
            messages.error(request, 'Link aktywacyjny jest nieprawidłowy lub wygasł.')
            return redirect('accounts:login')
