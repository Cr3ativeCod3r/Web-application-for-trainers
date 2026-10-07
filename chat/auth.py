import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError

from config import JWT_ALGORITHMS, JWT_AUDIENCE, JWT_ISSUER, JWT_PUBLIC_KEY

security = HTTPBearer()


def verify_token(token: str) -> int:
    """
    Validates a chat access token issued by the main app and returns the user id.

    The algorithm list is fixed: accepting the algorithm named in the token header
    would let an attacker sign an HS256 token using the *public* key as the secret.
    """
    try:
        payload = jwt.decode(
            token,
            JWT_PUBLIC_KEY,
            algorithms=JWT_ALGORITHMS,
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER,
            options={'require': ['exp', 'iat', 'sub', 'aud', 'iss']},
        )
        return int(payload['sub'])
    except (InvalidTokenError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        ) from exc


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    return verify_token(credentials.credentials)
