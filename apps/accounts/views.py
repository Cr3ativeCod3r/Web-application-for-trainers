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
from .services import AuthService

from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit

User = get_user_model()

@method_decorator(ratelimit(key='ip', rate='5/m', block=True), name='dispatch')
@method_decorator(ratelimit(key='post:username', rate='5/m', block=True), name='dispatch')
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

@method_decorator(ratelimit(key='ip', rate='5/m', block=True), name='dispatch')
class TrainerRegisterView(CreateView):
    template_name = 'accounts/register.html'
    form_class = TrainerRegistrationForm
    success_url = reverse_lazy('accounts:registration_success')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('trainers:home_search')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        email = form.cleaned_data.get('email')
        password = form.cleaned_data.get('password')
        domain = self.request.get_host()
        
        # Utilize the Service Layer to execute business logic
        self.object = AuthService.register_trainer(email, password, domain)
        
        return redirect(self.success_url)

class RegistrationSuccessView(TemplateView):
    template_name = 'accounts/registration_success.html'

class ActivateAccountView(View):
    def get(self, request, uidb64, token):
        success, user = AuthService.activate_account(uidb64, token)
        
        if success:
            messages.success(request, 'Twoje konto zostało aktywowane. Możesz się teraz zalogować.')
        else:
            messages.error(request, 'Link aktywacyjny jest nieprawidłowy lub wygasł.')
            
        return redirect('accounts:login')
