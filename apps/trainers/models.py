from django.db import models
from django.conf import settings

from django.utils.text import slugify
from autoslug import AutoSlugField

class Sport(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Nazwa sportu")
    slug = AutoSlugField(populate_from='name', unique=True, max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Dyscyplina sportowa"
        verbose_name_plural = "Dyscypliny sportowe"
        ordering = ['name']

class TrainerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='trainer_profile')
    username = models.SlugField(max_length=255, unique=True, verbose_name="Nazwa użytkownika (będzie w URL profilu)")
    
    full_name = models.CharField(max_length=255, verbose_name="Imię")
    sports = models.ManyToManyField(Sport, related_name='trainers', verbose_name="Dyscypliny", blank=True)
    location = models.CharField(max_length=255, verbose_name="Lokalizacja zajęć")
    headline = models.CharField(max_length=255, verbose_name="Header (Nagłówek profilu)")
    description = models.TextField(verbose_name="Opis")
    classes_description = models.TextField(verbose_name="Opis zajęć", help_text="Opisz, jak wyglądają Twoje zajęcia", blank=True, null=True)
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Stawka godzinowa (PLN)")
    
    contact_email = models.EmailField(verbose_name="Email kontaktowy")
    contact_phone = models.CharField(max_length=20, verbose_name="Telefon kontaktowy (opcjonalnie)", blank=True, null=True)
    
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

    def __str__(self):
        return f"{self.full_name} ({self.user.email})"

class TrainerProfileUpdate(models.Model):
    profile = models.OneToOneField(TrainerProfile, on_delete=models.CASCADE, related_name='pending_update')
    
    full_name = models.CharField(max_length=255, verbose_name="Imię")
    sports = models.ManyToManyField(Sport, related_name='profile_updates', verbose_name="Dyscypliny", blank=True)
    location = models.CharField(max_length=255, verbose_name="Lokalizacja zajęć")
    headline = models.CharField(max_length=255, verbose_name="Krótki nagłówek profilu (np. Trener Personalny)")
    description = models.TextField(verbose_name="Opis")
    classes_description = models.TextField(verbose_name="Opis zajęć", help_text="Opisz, jak wyglądają Twoje zajęcia", blank=True, null=True)
    hourly_rate = models.DecimalField(max_digits=6, decimal_places=2, verbose_name="Stawka godzinowa (PLN)")
    contact_email = models.EmailField(verbose_name="E-mail kontaktowy")
    contact_phone = models.CharField(max_length=20, verbose_name="Nr telefonu kontaktowy", blank=True, null=True)
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

    def __str__(self):
        return f"Oczekująca zmiana: {self.full_name}"

class TrainerPost(models.Model):
    trainer = models.ForeignKey(TrainerProfile, on_delete=models.CASCADE, related_name='posts')
    title = models.CharField(max_length=255, verbose_name="Tytuł posta")
    slug = AutoSlugField(populate_from='title', unique=True, max_length=255, verbose_name="Slug (URL)")
    image = models.ImageField(upload_to='post_images/', verbose_name="Zdjęcie", blank=True, null=True)
    content = models.TextField(verbose_name="Treść posta")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Data dodania")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']



    def __str__(self):
        return f"{self.title} - {self.trainer.full_name}"
