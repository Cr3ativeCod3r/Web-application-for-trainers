from django import forms

from .models import TrainerPost, TrainerProfile, TrainerProfileUpdate

# Explicit allow-lists (not `exclude`): a field added to the model later must not become
# user-editable by accident, and the order below is the order fields are rendered in.
PROFILE_FORM_FIELDS = [
    'full_name', 'sports', 'location', 'headline', 'tags', 'description', 'classes_description',
    'hourly_rate', 'contact_email', 'contact_phone', 'profile_picture',
    'instagram', 'facebook', 'tiktok', 'gender', 'training_type',
]


class CommaSeparatedTagsField(forms.CharField):
    def prepare_value(self, value):
        if isinstance(value, list):
            return ", ".join(value)
        return value

    def clean(self, value):
        value = super().clean(value)
        if not value:
            return []
        tags = [t.strip() for t in value.split(',') if t.strip()]
        if len(tags) > 5:
            raise forms.ValidationError("Możesz dodać maksymalnie 5 tagów.")
        return tags

class TrainerApplicationForm(forms.ModelForm):
    tags = CommaSeparatedTagsField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'np. sport, granie, zdrowie (oddziel przecinkami, max 5)'}),
        label="Tagi (np. sport, granie, max 5)"
    )

    class Meta:
        model = TrainerProfile
        fields = ['username', *PROFILE_FORM_FIELDS]
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



class TrainerProfileUpdateForm(forms.ModelForm):
    tags = CommaSeparatedTagsField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'np. sport, granie, zdrowie (oddziel przecinkami, max 5)'}),
        label="Tagi (np. sport, granie, max 5)"
    )

    class Meta:
        model = TrainerProfileUpdate
        fields = PROFILE_FORM_FIELDS
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
