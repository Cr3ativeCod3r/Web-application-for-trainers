import os
import socket
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
load_dotenv(os.path.join(BASE_DIR, '.env'))



def env_bool(name: str, default: bool = False) -> bool:
    return str(os.environ.get(name, default)).lower() in ('true', '1', 't', 'yes')


def env_list(name: str, default: str = '') -> list[str]:
    return [item.strip() for item in os.environ.get(name, default).split(',') if item.strip()]


def env_secret(name: str) -> str | None:
    """Read a secret from NAME, or from the file NAME_FILE points to (Docker/K8s secrets)."""
    if value := os.environ.get(name):
        return value
    if path := os.environ.get(f'{name}_FILE'):
        return Path(path).read_text()
    return None


# The secret key signs sessions and password-reset tokens.
# There is deliberately no fallback: a key committed to the repository is public.
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise ImproperlyConfigured('SECRET_KEY environment variable is not set.')

# Secure by default: debug mode has to be enabled explicitly (e.g. in .env for local dev).
DEBUG = env_bool('DEBUG', False)

API_GEMINI = os.environ.get('API_GEMINI', '')

ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', 'localhost,127.0.0.1')
CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS')

DOMAIN = os.environ.get('DOMAIN', 'localhost:8000')


# Application definition

LOCAL_APPS = [
    'apps.accounts',
    'apps.trainers',
    'apps.pages',
    'apps.admin_dashboard',
    'apps.events',
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.postgres',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'django_cleanup.apps.CleanupConfig',
    'storages',
] + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'core.middleware.RatelimitMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'trainapp'),
        'USER': os.environ.get('DB_USER', 'trainuser'),
        'PASSWORD': os.environ.get('DB_PASS', 'trainpass'),
        'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

# Django Debug Toolbar is a development tool only - it exposes SQL, settings and
# request data, so it is never installed when DEBUG is off.
if DEBUG:
    INSTALLED_APPS.append('debug_toolbar')
    MIDDLEWARE.insert(1, 'debug_toolbar.middleware.DebugToolbarMiddleware')
    hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
    INTERNAL_IPS = [ip[: ip.rfind(".")] + ".1" for ip in ips] + ["127.0.0.1", "10.0.2.2"]
# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/


LANGUAGE_CODE = 'pl'

TIME_ZONE = 'Europe/Warsaw'

USE_I18N = True

USE_TZ = True




# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Static files are served by WhiteNoise (gzip/brotli, long cache headers), so the
# app works behind gunicorn without a separate static file server.
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

AUTH_USER_MODEL = 'accounts.CustomUser'
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'trainers:home_search'
LOGOUT_REDIRECT_URL = 'trainers:home_search'

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# Cloudflare R2 Storage Configuration
USE_R2 = os.environ.get('USE_R2', 'False') == 'True'

if USE_R2:
    AWS_ACCESS_KEY_ID = os.environ.get('R2_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('R2_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.environ.get('R2_BUCKET_NAME')
    AWS_S3_ENDPOINT_URL = os.environ.get('R2_ENDPOINT_URL')
    AWS_S3_REGION_NAME = 'auto'  # Cloudflare R2 requires 'auto'

    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = None

    # If you have a public custom domain connected to R2, set it here (e.g., cdn.twojadomena.pl or pub-...r2.dev)
    r2_custom_domain = os.environ.get('R2_CUSTOM_DOMAIN')
    if r2_custom_domain:
        AWS_S3_CUSTOM_DOMAIN = r2_custom_domain

    STORAGES["default"] = {"BACKEND": "storages.backends.s3boto3.S3Boto3Storage"}
else:
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

SITE_ID = 1

# Google is the only allauth flow in use (e-mail/password auth has its own views);
# Google already verifies the address, so allauth does not send its own e-mail.
ACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*']
ACCOUNT_USER_MODEL_USERNAME_FIELD = None

SOCIALACCOUNT_ADAPTER = 'apps.accounts.adapters.CustomSocialAccountAdapter'

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APPS': [
            {
                'client_id': os.environ.get('GOOGLE_CLIENT_ID', '').strip(),
                'secret': os.environ.get('GOOGLE_CLIENT_SECRET', '').strip(),
                'key': ''
            }
        ],
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        }
    }
}

# Celery Configuration
CELERY_BROKER_URL = os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

CELERY_BEAT_SCHEDULE = {
    # Safety net for the on-commit trigger (e.g. broker briefly down): nothing stays
    # in the outbox for longer than this interval.
    'relay-outbox-events': {
        'task': 'apps.events.tasks.relay_outbox_events',
        'schedule': 15.0,
    },
    'purge-published-outbox-events': {
        'task': 'apps.events.tasks.purge_published_outbox_events',
        'schedule': 60 * 60 * 24,
    },
}

# Message bus for integration events between services (Redis Streams).
EVENT_BUS_URL = os.environ.get('EVENT_BUS_URL', os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0'))
EVENT_STREAM_MAXLEN = 100_000

# Redis Cache for Rate Limiting & Performance
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0'),
    }
}

# Tokens for the chat microservice (see apps/accounts/chat_tokens.py). The private
# key never leaves this app; the chat service is configured with the public key.
JWT_PRIVATE_KEY = env_secret('JWT_PRIVATE_KEY')
if not JWT_PRIVATE_KEY:
    raise ImproperlyConfigured(
        'JWT_PRIVATE_KEY (or JWT_PRIVATE_KEY_FILE) is not set. Generate keys with scripts/generate_jwt_keys.sh.'
    )
CHAT_TOKEN_ISSUER = 'coachly-web'
CHAT_TOKEN_AUDIENCE = 'coachly-chat'
# Short on purpose: the page asks for a fresh token whenever it needs one.
CHAT_TOKEN_LIFETIME = 5 * 60

CHAT_API_URL = os.environ.get('CHAT_API_URL', 'http://localhost:8001')
CHAT_WS_URL = os.environ.get('CHAT_WS_URL', 'ws://localhost:8001')

# Production hardening (only when DEBUG is off, so local HTTP development keeps working)
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', 60 * 60 * 24 * 30))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
