from allauth.socialaccount.models import SocialAccount
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
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


class StatusTransition(models.TextChoices):
    """
    Named steps of the trainer lifecycle. They are named (not just "status A -> B")
    because two different steps can end in the same status: approving an application
    and lifting a ban both lead to APPROVED_TRAINER, but only from their own source.
    """
    APPLY = 'apply', 'Złożenie wniosku'
    APPROVE = 'approve', 'Zatwierdzenie'
    BAN = 'ban', 'Zawieszenie'
    UNBAN = 'unban', 'Odwieszenie'


STATUS_TRANSITIONS: dict[str, tuple[str, str]] = {
    StatusTransition.APPLY: (TrainerStatus.REGISTERED, TrainerStatus.PENDING_APPLICATION),
    StatusTransition.APPROVE: (TrainerStatus.PENDING_APPLICATION, TrainerStatus.APPROVED_TRAINER),
    StatusTransition.BAN: (TrainerStatus.APPROVED_TRAINER, TrainerStatus.BANNED),
    StatusTransition.UNBAN: (TrainerStatus.BANNED, TrainerStatus.APPROVED_TRAINER),
}


class InvalidStatusTransition(Exception):
    def __init__(self, transition: str, current: str):
        self.transition = transition
        self.current = current
        super().__init__(f"Cannot '{transition}' an account with status {current}")


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
        verbose_name = "Normal accounts"
        verbose_name_plural = "Accounts registered normally"

    def __str__(self):
        return self.email

    def can_apply_transition(self, transition: str) -> bool:
        source, _target = STATUS_TRANSITIONS[transition]
        return self.status == source

    def apply_transition(self, transition: str) -> None:
        """Change the status in memory, enforcing the lifecycle. The caller saves."""
        if not self.can_apply_transition(transition):
            raise InvalidStatusTransition(transition, self.status)
        _source, self.status = STATUS_TRANSITIONS[transition]

class ClientProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='client_profile')
    first_name = models.CharField(max_length=50, verbose_name="Imię")
    last_name = models.CharField(max_length=50, verbose_name="Nazwisko")

    class Meta:
        verbose_name = "Profil klienta"
        verbose_name_plural = "Profile klientów"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class GoogleAccount(SocialAccount):
    class Meta:
        proxy = True
        verbose_name = "Konto Google"
        verbose_name_plural = "Accounts registered via Google"
