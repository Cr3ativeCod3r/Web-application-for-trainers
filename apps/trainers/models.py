from django.db import models
from django.conf import settings
from django.contrib.postgres.fields import ArrayField

from autoslug import AutoSlugField

from core.html import sanitize_html

class Sport(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Nazwa sportu")
    slug = AutoSlugField(populate_from='name', unique=True, max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Dyscyplina sportowa"
        verbose_name_plural = "Dyscypliny sportowe"
        ordering = ['name']

class Gender(models.TextChoices):
    MALE = 'M', 'Chłopak'
    FEMALE = 'F', 'Dziewczyna'


class TrainingType(models.TextChoices):
    STATIONARY = 'STATIONARY', 'Stacjonarnie'
    ONLINE = 'ONLINE', 'Online'
    BOTH = 'BOTH', 'Online & Stacjonarnie'


class TrainerProfileContent(models.Model):
    """
    Fields a trainer can edit. Shared by the live profile and the pending update
    awaiting moderation, so both always have the same schema and validation.
    (`sports` and `profile_picture` are declared on the concrete models because
    they need a different related_name / upload directory.)
    """
    full_name = models.CharField(max_length=255, verbose_name="Imię")
    location = models.CharField(max_length=255, verbose_name="Lokalizacja zajęć")
    headline = models.CharField(max_length=255, verbose_name="Krótki nagłówek profilu (np. Trener Personalny)")
    tags = ArrayField(
        models.CharField(max_length=30),
        size=5,
        blank=True,
        default=list,
        verbose_name="Tagi (np. sport, granie, max 5)"
    )
    description = models.TextField(verbose_name="Opis")
    classes_description = models.TextField(verbose_name="Opis zajęć", help_text="Opisz, jak wyglądają Twoje zajęcia", blank=True, null=True)
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Stawka godzinowa (PLN)")

    contact_email = models.EmailField(verbose_name="E-mail kontaktowy")
    contact_phone = models.CharField(max_length=20, verbose_name="Telefon kontaktowy (opcjonalnie)", blank=True, null=True)

    tiktok = models.URLField(blank=True, null=True, verbose_name="TikTok (opcjonalnie)")
    instagram = models.URLField(blank=True, null=True, verbose_name="Instagram (opcjonalnie)")
    facebook = models.URLField(blank=True, null=True, verbose_name="Facebook (opcjonalnie)")

    gender = models.CharField(max_length=1, choices=Gender.choices, verbose_name="Płeć", blank=True, null=True)
    training_type = models.CharField(max_length=15, choices=TrainingType.choices, verbose_name="Typ zajęć", default=TrainingType.STATIONARY)

    class Meta:
        abstract = True

    @classmethod
    def content_field_names(cls) -> list[str]:
        """Names of the plain (non-relational, non-file) editable fields."""
        return [field.name for field in TrainerProfileContent._meta.fields]


class TrainerProfile(TrainerProfileContent):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='trainer_profile')
    username = models.SlugField(max_length=255, unique=True, verbose_name="Nazwa użytkownika (będzie w URL profilu)")
    sports = models.ManyToManyField(Sport, related_name='trainers', verbose_name="Dyscypliny", blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True, verbose_name="Zdjęcie profilowe")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.full_name} ({self.user.email})"


class TrainerProfileUpdate(TrainerProfileContent):
    """A pending edit of a TrainerProfile; applied only after admin approval."""
    profile = models.OneToOneField(TrainerProfile, on_delete=models.CASCADE, related_name='pending_update')
    sports = models.ManyToManyField(Sport, related_name='profile_updates', verbose_name="Dyscypliny", blank=True)
    profile_picture = models.ImageField(upload_to='pending_profile_pics/', blank=True, null=True, verbose_name="Zdjęcie profilowe")

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

    def save(self, *args, **kwargs):
        # Content is rendered with |safe, so it is sanitized on every write path
        # (form, Django admin, shell, seed commands) - not only in the form.
        self.content = sanitize_html(self.content)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} - {self.trainer.full_name}"
