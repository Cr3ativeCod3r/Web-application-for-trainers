from django import forms
from .models import TrainerProfile

class TrainerApplicationForm(forms.ModelForm):
    class Meta:
        model = TrainerProfile
        exclude = ('user', 'created_at', 'updated_at')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'classes_description': forms.Textarea(attrs={'rows': 4}),
            'profile_picture': forms.FileInput(attrs={'accept': 'image/png'}),
            'sports': forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['gender'].required = True
        self.fields['gender'].empty_label = "Wybierz płeć..."

    def clean_profile_picture(self):
        picture = self.cleaned_data.get('profile_picture', False)
        if picture:
            if not picture.name.lower().endswith('.png'):
                raise forms.ValidationError("Zdjęcie musi być w formacie PNG.")
            if hasattr(picture, 'content_type') and picture.content_type != 'image/png':
                raise forms.ValidationError("Zdjęcie musi być w formacie PNG.")
        return picture

    def clean_username(self):
        username = self.cleaned_data.get('username')
        reserved_usernames = ['aplikuj', 'zarzadzaj', 'admin', 'trenerzy', 'trener', 'login', 'rejestracja', 'api']
        if username.lower() in reserved_usernames:
            raise forms.ValidationError("Ta nazwa użytkownika jest zarezerwowana przez system.")
        return username

from .models import TrainerProfileUpdate

class TrainerProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = TrainerProfileUpdate
        exclude = ('profile', 'created_at')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'classes_description': forms.Textarea(attrs={'rows': 4}),
            'profile_picture': forms.FileInput(attrs={'accept': 'image/png'}),
            'sports': forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['gender'].required = True
        self.fields['gender'].empty_label = "Wybierz płeć..."

    def clean_profile_picture(self):
        picture = self.cleaned_data.get('profile_picture', False)
        if picture:
            if not picture.name.lower().endswith('.png'):
                raise forms.ValidationError("Zdjęcie musi być w formacie PNG.")
            if hasattr(picture, 'content_type') and picture.content_type != 'image/png':
                raise forms.ValidationError("Zdjęcie musi być w formacie PNG.")
        return picture

from .models import TrainerPost

class TrainerPostForm(forms.ModelForm):
    class Meta:
        model = TrainerPost
        fields = ['title', 'image', 'content']
        widgets = {
            'content': forms.Textarea(attrs={'class': 'wysiwyg-editor'}),
            'title': forms.TextInput(attrs={
                'class': 'w-full border-gray-300 rounded-xl shadow-sm focus:border-primary focus:ring-primary px-4 py-3 text-lg'
            }),
            'image': forms.FileInput(attrs={'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl bg-gray-50'}),
        }
