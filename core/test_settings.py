from .settings import *  # noqa: F401,F403

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
