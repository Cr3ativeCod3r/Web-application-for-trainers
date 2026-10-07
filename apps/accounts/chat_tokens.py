"""
Short-lived access tokens for the chat microservice.

Signed with an asymmetric key (ES256): this app holds the private key, the chat
service only the public one, so a compromised chat service cannot mint tokens.
The audience/issuer claims stop the token from being accepted anywhere else.
"""
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from django.conf import settings

ALGORITHM = 'ES256'


def issue_chat_token(user) -> tuple[str, int]:
    """Returns (token, lifetime in seconds)."""
    lifetime = settings.CHAT_TOKEN_LIFETIME
    now = datetime.now(UTC)
    claims = {
        'iss': settings.CHAT_TOKEN_ISSUER,
        'aud': settings.CHAT_TOKEN_AUDIENCE,
        'sub': str(user.pk),
        'iat': now,
        'exp': now + timedelta(seconds=lifetime),
        'jti': uuid.uuid4().hex,
    }
    token = jwt.encode(claims, settings.JWT_PRIVATE_KEY, algorithm=ALGORITHM)
    return token, lifetime
