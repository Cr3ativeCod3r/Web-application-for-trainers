import os

# Tests must behave the same on every machine and in CI, regardless of a developer's
# .env (load_dotenv never overrides variables that are already set):
# - always run with production-like DEBUG=False (no debug toolbar, secure defaults),
# - provide a throwaway key if none is set.
os.environ['DEBUG'] = 'False'
os.environ.setdefault('SECRET_KEY', 'test-only-insecure-secret-key-not-for-production-use')
if not (os.environ.get('JWT_PRIVATE_KEY') or os.environ.get('JWT_PRIVATE_KEY_FILE')):
    # A throwaway key per test run; tests derive the public key from it.
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    os.environ['JWT_PRIVATE_KEY'] = ec.generate_private_key(ec.SECP256R1()).private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    ).decode()

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

# Uploaded files from tests go to a throwaway directory, not the project's media/.
import tempfile  # noqa: E402

MEDIA_ROOT = tempfile.mkdtemp(prefix='coachly-test-media-')
