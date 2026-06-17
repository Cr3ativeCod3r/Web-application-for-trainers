from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Adres email jest wymagany')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('status', TrainerStatus.ADMIN)
        extra_fields.setdefault('is_active', True)
        return self.create_user(email, password, **extra_fields)

class TrainerStatus(models.TextChoices):
    REGISTERED = 'REGISTERED', 'Zarejestrowany'
    PENDING_APPLICATION = 'PENDING_APPLICATION', 'Złożono wniosek'
    APPROVED_TRAINER = 'APPROVED_TRAINER', 'Trener'
    BANNED = 'BANNED', 'Zbanowany'
    ADMIN = 'ADMIN', 'Administrator'

class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, verbose_name="Adres e-mail")
    status = models.CharField(
        max_length=30,
        choices=TrainerStatus.choices,
        default=TrainerStatus.REGISTERED,
        verbose_name="Status konta"
    )
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "Konto normalne"
        verbose_name_plural = "Konta zarejestrowane normalnie"

    def __str__(self):
        return self.email

from allauth.socialaccount.models import SocialAccount

class GoogleAccount(SocialAccount):
    class Meta:
        proxy = True
        verbose_name = "Konto Google"
        verbose_name_plural = "Konta zarejestrowane z Google"
