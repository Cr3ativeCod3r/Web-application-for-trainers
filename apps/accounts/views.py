from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView, View
from django.views.generic.edit import CreateView
from django_ratelimit.decorators import ratelimit
from rest_framework_simplejwt.tokens import RefreshToken

from .forms import ClientRegistrationForm, CustomAuthenticationForm, TrainerRegistrationForm
from .models import TrainerStatus
from .selectors import get_user_display_info, users_share_chat_room
from .services import AuthService

User = get_user_model()

REMEMBER_ME_SESSION_AGE = 60 * 60 * 24 * 14  # 2 weeks


def wants_json(request) -> bool:
    return request.headers.get('Accept') == 'application/json'


class RememberMeLoginMixin:
    """Keeps the session for two weeks when "remember me" is ticked, otherwise until the browser closes."""

    def form_valid(self, form):
        remember_me = form.cleaned_data.get('remember_me')
        self.request.session.set_expiry(REMEMBER_ME_SESSION_AGE if remember_me else 0)
        return super().form_valid(form)


login_ratelimits = [
    ratelimit(key='ip', rate='5/m', block=True),
    ratelimit(key='post:username', rate='5/m', block=True),
]


# --- Clients ---------------------------------------------------------------

@method_decorator(ratelimit(key='ip', rate='5/m', block=True), name='dispatch')
class ClientRegisterView(CreateView):
    template_name = 'accounts/client_register.html'
    form_class = ClientRegistrationForm
    success_url = reverse_lazy('trainers:home_search')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if wants_json(request):
                return JsonResponse({'success': True, 'redirect': str(self.success_url)})
            return redirect(self.success_url)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = AuthService.register_client(
            form.cleaned_data['email'],
            form.cleaned_data['password'],
            self.request.get_host(),
            first_name=form.cleaned_data['first_name'],
            last_name=form.cleaned_data['last_name'],
        )

        if wants_json(self.request):
            return JsonResponse({'success': True, 'message': 'Konto zostało utworzone. Sprawdź swoją skrzynkę e-mail, aby je aktywować!'})

        messages.success(self.request, "Rejestracja przebiegła pomyślnie! Sprawdź e-mail, by aktywować konto.")
        return redirect(self.success_url)

    def form_invalid(self, form):
        if wants_json(self.request):
            return JsonResponse({'success': False, 'errors': form.errors})
        return super().form_invalid(form)


@method_decorator(login_ratelimits, name='dispatch')
class ClientLoginView(RememberMeLoginMixin, LoginView):
    template_name = 'accounts/client_login.html'
    form_class = CustomAuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        # LoginView.get_redirect_url() validates `next` with url_has_allowed_host_and_scheme,
        # so only same-host redirects are honoured (no open redirect to phishing sites).
        return self.get_redirect_url() or str(reverse_lazy('trainers:home_search'))

    def form_valid(self, form):
        response = super().form_valid(form)
        if wants_json(self.request):
            return JsonResponse({'success': True, 'redirect': self.get_success_url()})
        return response

    def form_invalid(self, form):
        if wants_json(self.request):
            return JsonResponse({'success': False, 'errors': form.errors})
        return super().form_invalid(form)


# --- Trainers --------------------------------------------------------------

@method_decorator(login_ratelimits, name='dispatch')
class TrainerLoginView(RememberMeLoginMixin, LoginView):
    template_name = 'trainers/login.html'
    form_class = CustomAuthenticationForm
    redirect_authenticated_user = True


@method_decorator(ratelimit(key='ip', rate='5/m', block=True), name='dispatch')
class TrainerRegisterView(CreateView):
    template_name = 'trainers/register.html'
    form_class = TrainerRegistrationForm
    success_url = reverse_lazy('trainers:registration_success')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('trainers:home_search')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = AuthService.register_trainer(
            form.cleaned_data['email'],
            form.cleaned_data['password'],
            self.request.get_host(),
        )
        return redirect(self.success_url)


class TrainerRegistrationSuccessView(TemplateView):
    template_name = 'trainers/registration_success.html'


# --- Shared ----------------------------------------------------------------

class ActivateAccountView(View):
    def get(self, request, uidb64, token):
        success, _user = AuthService.activate_account(uidb64, token)

        if success:
            messages.success(request, 'Twoje konto zostało aktywowane. Możesz się teraz zalogować.')
        else:
            messages.error(request, 'Link aktywacyjny jest nieprawidłowy lub wygasł.')

        return redirect('accounts:login')


class ChatView(LoginRequiredMixin, TemplateView):
    template_name = 'chat/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        info = get_user_display_info(self.request.user)
        context.update({
            'jwt_token': str(RefreshToken.for_user(self.request.user).access_token),
            'current_user_name': info['name'],
            'current_user_avatar': info['avatar_url'],
            'chat_api_url': settings.CHAT_API_URL,
            'chat_ws_url': settings.CHAT_WS_URL,
        })
        return context


@login_required
def user_info_api(request, user_id):
    """
    Returns display info (name + avatar) for a chat partner - used by the chat JS.

    Approved trainers are public anyway; any other user is only visible to people
    they actually have a conversation with, so ids cannot be enumerated to harvest
    names of all clients.
    """
    target = User.objects.select_related('trainer_profile', 'client_profile').filter(pk=user_id).first()
    if target is None:
        return JsonResponse({'error': 'not found'}, status=404)

    is_public_trainer = target.status == TrainerStatus.APPROVED_TRAINER
    if not (is_public_trainer or target.pk == request.user.pk or users_share_chat_room(request.user.pk, target.pk)):
        return JsonResponse({'error': 'not found'}, status=404)

    return JsonResponse(get_user_display_info(target))
