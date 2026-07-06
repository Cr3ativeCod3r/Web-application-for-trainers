from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
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



from .forms import ClientRegistrationForm
from django.contrib.auth import login

from django.http import JsonResponse
from .services import AuthService
from .models import ClientProfile

@method_decorator(ratelimit(key='ip', rate='5/m', block=True), name='dispatch')
class ClientRegisterView(CreateView):
    template_name = 'accounts/client_register.html'
    form_class = ClientRegistrationForm
    success_url = reverse_lazy('trainers:home_search')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.headers.get('Accept') == 'application/json':
                return JsonResponse({'success': True, 'redirect': str(self.success_url)})
            return redirect('trainers:home_search')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        email = form.cleaned_data.get('email')
        password = form.cleaned_data.get('password')
        domain = self.request.get_host()

        # Register as client with client-specific activation email
        user = AuthService.register_client(email, password, domain)
        ClientProfile.objects.create(
            user=user,
            first_name=form.cleaned_data['first_name'],
            last_name=form.cleaned_data['last_name']
        )

        if self.request.headers.get('Accept') == 'application/json':
            return JsonResponse({'success': True, 'message': 'Konto zostało utworzone. Sprawdź swoją skrzynkę e-mail, aby je aktywować!'})

        messages.success(self.request, "Rejestracja przebiegła pomyślnie! Sprawdź e-mail, by aktywować konto.")
        return redirect(self.success_url)

    def form_invalid(self, form):
        if self.request.headers.get('Accept') == 'application/json':
            return JsonResponse({'success': False, 'errors': form.errors})
        return super().form_invalid(form)

@method_decorator(ratelimit(key='ip', rate='5/m', block=True), name='dispatch')
@method_decorator(ratelimit(key='post:username', rate='5/m', block=True), name='dispatch')
class ClientLoginView(LoginView):
    template_name = 'accounts/client_login.html'
    form_class = CustomAuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        return reverse_lazy('trainers:home_search')

    def form_valid(self, form):
        remember_me = form.cleaned_data.get('remember_me')
        if not remember_me:
            self.request.session.set_expiry(0)
            self.request.session.modified = True
        else:
            self.request.session.set_expiry(1209600)
            self.request.session.modified = True
            
        super().form_valid(form)
        if self.request.headers.get('Accept') == 'application/json':
            return JsonResponse({'success': True, 'redirect': str(self.get_success_url())})
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        if self.request.headers.get('Accept') == 'application/json':
            return JsonResponse({'success': False, 'errors': form.errors})
        return super().form_invalid(form)

from django.views.generic import View, TemplateView

class ActivateAccountView(View):
    def get(self, request, uidb64, token):
        success, user = AuthService.activate_account(uidb64, token)
        
        if success:
            messages.success(request, 'Twoje konto zostało aktywowane. Możesz się teraz zalogować.')
        else:
            messages.error(request, 'Link aktywacyjny jest nieprawidłowy lub wygasł.')
            
        return redirect('accounts:login')

