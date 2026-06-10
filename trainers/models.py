from django.db import models
from django.conf import settings

class TrainerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='trainer_profile')
    username = models.SlugField(max_length=255, unique=True, blank=True, verbose_name="Nazwa użytkownika (URL)")
    
    full_name = models.CharField(max_length=255, verbose_name="Imię")
    sport = models.CharField(max_length=255, verbose_name="Dyscypliny (oddziel przecinkami)", help_text="Np. Joga, Boks, Trening personalny")
    location = models.CharField(max_length=255, verbose_name="Lokalizacja zajęć")
    headline = models.CharField(max_length=255, verbose_name="Header (Nagłówek profilu)")
    description = models.TextField(verbose_name="Opis")
    classes_description = models.TextField(verbose_name="Opis zajęć", help_text="Opisz, jak wyglądają Twoje zajęcia", blank=True, null=True)
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Stawka godzinowa (PLN)")
    
    contact_email = models.EmailField(verbose_name="Email kontaktowy")
    contact_phone = models.CharField(max_length=20, verbose_name="Telefon kontaktowy")
    
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True, verbose_name="Zdjęcie profilowe")
    
    tiktok = models.URLField(blank=True, null=True, verbose_name="TikTok (opcjonalnie)")
    instagram = models.URLField(blank=True, null=True, verbose_name="Instagram (opcjonalnie)")
    facebook = models.URLField(blank=True, null=True, verbose_name="Facebook (opcjonalnie)")

    GENDER_CHOICES = [
        ('M', 'Chłopak'),
        ('F', 'Dziewczyna'),
    ]
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, verbose_name="Płeć", blank=True, null=True)

    TRAINING_TYPE_CHOICES = [
        ('STATIONARY', 'Stacjonarnie'),
        ('ONLINE', 'Online'),
        ('BOTH', 'Online & Stacjonarnie'),
    ]
    training_type = models.CharField(max_length=15, choices=TRAINING_TYPE_CHOICES, verbose_name="Typ zajęć", default='STATIONARY')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def sports_list(self):
        if not self.sport:
            return []
        return [s.strip() for s in self.sport.split(',') if s.strip()]

    def __str__(self):
        return f"{self.full_name} ({self.user.email})"

class TrainerProfileUpdate(models.Model):
    profile = models.OneToOneField(TrainerProfile, on_delete=models.CASCADE, related_name='pending_update')
    
    full_name = models.CharField(max_length=255, verbose_name="Imię")
    sport = models.CharField(max_length=255, verbose_name="Dyscypliny (oddziel przecinkami)", help_text="Np. Joga, Boks, Trening personalny")
    location = models.CharField(max_length=255, verbose_name="Lokalizacja zajęć")
    headline = models.CharField(max_length=255, verbose_name="Krótki nagłówek profilu (np. Trener Personalny)")
    description = models.TextField(verbose_name="Opis")
    classes_description = models.TextField(verbose_name="Opis zajęć", help_text="Opisz, jak wyglądają Twoje zajęcia", blank=True, null=True)
    hourly_rate = models.DecimalField(max_digits=6, decimal_places=2, verbose_name="Stawka godzinowa (PLN)")
    contact_email = models.EmailField(verbose_name="E-mail kontaktowy")
    contact_phone = models.CharField(max_length=20, verbose_name="Nr telefonu kontaktowy")
    profile_picture = models.ImageField(upload_to='pending_profile_pics/', blank=True, null=True, verbose_name="Zdjęcie profilowe")
    
    instagram = models.URLField(blank=True, null=True, verbose_name="Instagram (opcjonalnie)")
    facebook = models.URLField(blank=True, null=True, verbose_name="Facebook (opcjonalnie)")
    tiktok = models.URLField(blank=True, null=True, verbose_name="TikTok (opcjonalnie)")

    GENDER_CHOICES = [
        ('M', 'Chłopak'),
        ('F', 'Dziewczyna'),
    ]
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, verbose_name="Płeć", blank=True, null=True)

    TRAINING_TYPE_CHOICES = [
        ('STATIONARY', 'Stacjonarnie'),
        ('ONLINE', 'Online'),
        ('BOTH', 'Online & Stacjonarnie'),
    ]
    training_type = models.CharField(max_length=15, choices=TRAINING_TYPE_CHOICES, verbose_name="Typ zajęć", default='STATIONARY')

    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def sports_list(self):
        if not self.sport:
            return []
        return [s.strip() for s in self.sport.split(',') if s.strip()]

    def __str__(self):
        return f"Oczekująca zmiana: {self.full_name}"
