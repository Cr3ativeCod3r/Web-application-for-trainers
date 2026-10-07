import os
from pathlib import Path


def env_secret(name: str) -> str | None:
    """Read a secret from NAME, or from the file NAME_FILE points to (Docker/K8s secrets)."""
    if value := os.environ.get(name):
        return value
    if path := os.environ.get(f'{name}_FILE'):
        return Path(path).read_text()
    return None


# Public half of the main app's signing key: this service can verify tokens but
# never issue them. No fallback on purpose.
JWT_PUBLIC_KEY = env_secret('JWT_PUBLIC_KEY')
if not JWT_PUBLIC_KEY:
    raise RuntimeError('JWT_PUBLIC_KEY (or JWT_PUBLIC_KEY_FILE) is not set.')
JWT_ALGORITHMS = ['ES256']
JWT_ISSUER = 'coachly-web'
JWT_AUDIENCE = 'coachly-chat'

# Single-use tickets for opening a WebSocket (see main.create_ws_ticket).
WS_TICKET_TTL_SECONDS = 30

REDIS_URL = os.environ.get('REDIS_URL', 'redis://redis:6379/0')
REDIS_CHANNEL = 'chat_messages'
# Internal commands for every chat instance (e.g. "close this user's sockets").
CONTROL_CHANNEL = 'chat_control'

# Integration events published by the main app (see apps/events/contracts.py there).
USER_EVENTS_STREAM = 'coachly.users.v1'
USER_EVENTS_GROUP = 'chat-service'

CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get('CHAT_CORS_ORIGINS', 'http://localhost:8000,http://127.0.0.1:8000').split(',')
    if origin.strip()
]

SQL_ECHO = os.environ.get('SQL_ECHO', 'False').lower() in ('true', '1')

MAX_MESSAGE_LENGTH = 2000
# Flood protection per user, shared by all their tabs and all service instances.
MESSAGE_RATE_LIMIT = 10
MESSAGE_RATE_WINDOW_SECONDS = 5
DEFAULT_HISTORY_LIMIT = 100
MAX_HISTORY_LIMIT = 500
