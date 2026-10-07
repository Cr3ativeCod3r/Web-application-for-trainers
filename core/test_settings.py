import os

# Tests must behave the same on every machine and in CI, regardless of a developer's
# .env (load_dotenv never overrides variables that are already set):
# - always run with production-like DEBUG=False (no debug toolbar, secure defaults),
# - provide a throwaway key if none is set.
os.environ['DEBUG'] = 'False'
os.environ.setdefault('SECRET_KEY', 'test-only-insecure-secret-key-not-for-production-use')

from .settings import *  # noqa: E402,F401,F403

# Tests run against PostgreSQL (configured via the same DB_* env vars as the app).
# SQLite cannot be used here: the models rely on Postgres-only features such as
# ArrayField (TrainerProfile.tags), so a SQLite test DB fails at migration time.

# Use a faster password hasher for testing
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Keep tests self-contained: no Redis, no SMTP, no Celery broker required.
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# The Django test client speaks plain HTTP; redirecting it to https:// would turn
# every response into a 301. HTTPS enforcement is a deployment concern.
SECURE_SSL_REDIRECT = False
