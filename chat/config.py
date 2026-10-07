import os

# Shared with Django: Django signs the JWT, this service verifies it. No fallback on purpose.
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise RuntimeError('SECRET_KEY environment variable is not set.')

REDIS_URL = os.environ.get('REDIS_URL', 'redis://redis:6379/0')
REDIS_CHANNEL = 'chat_messages'

CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get('CHAT_CORS_ORIGINS', 'http://localhost:8000,http://127.0.0.1:8000').split(',')
    if origin.strip()
]

SQL_ECHO = os.environ.get('SQL_ECHO', 'False').lower() in ('true', '1')

MAX_MESSAGE_LENGTH = 2000
# Minimum delay between two messages from one connection (server-side flood protection).
MIN_SECONDS_BETWEEN_MESSAGES = 0.5
DEFAULT_HISTORY_LIMIT = 100
MAX_HISTORY_LIMIT = 500
