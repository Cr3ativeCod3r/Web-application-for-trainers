from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model

User = get_user_model()

class TrainerRegistrationForm(forms.ModelForm):
    password = forms.CharField(
        label="Hasło",
        widget=forms.PasswordInput(attrs={'placeholder': 'Twoje hasło'})
    )

    class Meta:
        model = User
        fields = ('email',)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user

class ClientRegistrationForm(forms.ModelForm):
    first_name = forms.CharField(label="Imię", max_length=50, widget=forms.TextInput(attrs={'placeholder': 'Twoje imię'}))
    last_name = forms.CharField(label="Nazwisko", max_length=50, widget=forms.TextInput(attrs={'placeholder': 'Twoje nazwisko'}))
    password = forms.CharField(
        label="Hasło",
        widget=forms.PasswordInput(attrs={'placeholder': 'Twoje hasło'})
    )

    class Meta:
        model = User
        fields = ('email',)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        # Status remains REGISTERED for standard users
        user.is_active = True # We can auto-activate clients or keep email verification? User said simple. Let's auto-activate for now, or use the existing AuthService flow. 
        if commit:
            user.save()
            from .models import ClientProfile
            ClientProfile.objects.create(
                user=user,
                first_name=self.cleaned_data["first_name"],
                last_name=self.cleaned_data["last_name"]
            )
        return user

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

from django.contrib.auth.forms import SetPasswordForm

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

    def clean(self):
        # Skip validation comparing two passwords from the base class
        password = self.cleaned_data.get('new_password1')
        return self.cleaned_data

    def save(self, commit=True):
        password = self.cleaned_data["new_password1"]
        self.user.set_password(password)
        if commit:
            self.user.save()
        return self.user
