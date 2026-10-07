from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, SetPasswordForm
from django.contrib.auth.password_validation import validate_password

User = get_user_model()


class PasswordValidationMixin:
    """Runs AUTH_PASSWORD_VALIDATORS (length, common passwords, similarity to e-mail...)."""

    def clean_password(self):
        password = self.cleaned_data.get('password')
        candidate = User(email=self.cleaned_data.get('email', ''))
        validate_password(password, user=candidate)
        return password


# Registration forms only validate input; user creation lives in AuthService.
class TrainerRegistrationForm(PasswordValidationMixin, forms.ModelForm):
    password = forms.CharField(
        label="Hasło",
        widget=forms.PasswordInput(attrs={'placeholder': 'Twoje hasło'})
    )

    class Meta:
        model = User
        fields = ('email',)

class ClientRegistrationForm(PasswordValidationMixin, forms.ModelForm):
    first_name = forms.CharField(label="Imię", max_length=50, widget=forms.TextInput(attrs={'placeholder': 'Twoje imię'}))
    last_name = forms.CharField(label="Nazwisko", max_length=50, widget=forms.TextInput(attrs={'placeholder': 'Twoje nazwisko'}))
    password = forms.CharField(
        label="Hasło",
        widget=forms.PasswordInput(attrs={'placeholder': 'Twoje hasło'})
    )

    class Meta:
        model = User
        fields = ('email',)


class CustomAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label="Adres e-mail",
        widget=forms.EmailInput(attrs={'autofocus': True, 'placeholder': 'Twój e-mail'})
    )
    remember_me = forms.BooleanField(required=False, label="Zapamiętaj mnie")

    error_messages = {
        'invalid_login': "Wprowadź poprawny adres e-mail i hasło. Pamiętaj, że wielkość liter ma znaczenie.",
        'inactive': "Aby się zalogować, najpierw potwierdź swój adres e-mail, klikając w link z wiadomości rejestracyjnej.",
    }


class SinglePasswordSetForm(SetPasswordForm):
    new_password1 = forms.CharField(
        label="Nowe hasło",
        widget=forms.PasswordInput(attrs={'placeholder': 'Wpisz nowe hasło'})
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        # Remove the second confirmation field
        if 'new_password2' in self.fields:
            del self.fields['new_password2']

    def clean_new_password1(self):
        # Only one password field is shown, so there is nothing to compare,
        # but the strength validators still have to run.
        password = self.cleaned_data.get('new_password1')
        validate_password(password, self.user)
        return password

    def clean(self):
        # Skip the base class check that compares new_password1 with new_password2.
        return self.cleaned_data

    def save(self, commit=True):
        password = self.cleaned_data["new_password1"]
        self.user.set_password(password)
        if commit:
            self.user.save()
        return self.user
