from django import forms


class ContactForm(forms.Form):
    name = forms.CharField(max_length=100)
    email = forms.EmailField()
    message = forms.CharField(max_length=5000)

    def clean_name(self):
        name = self.cleaned_data['name']
        # The name goes into the e-mail subject; line breaks there are header injection.
        if '\n' in name or '\r' in name:
            raise forms.ValidationError("Imię nie może zawierać znaków nowej linii.")
        return name
